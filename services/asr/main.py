"""
services/asr/main.py
Real-time Uzbek/Russian ASR using faster-whisper + pyannote + silero-VAD.
Emits TranscriptWord events via WebSocket.

Phase 0: stub mode (USE_STUB=true) emits fake events.
Phase 1: real model mode.
"""
import asyncio, json, os, sys, time, random, uuid
from pathlib import Path
import websockets
from loguru import logger

# ── path so we can import shared types ──────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parents[2]))
from shared.types.models import TranscriptWord, TranscriptChunk

USE_STUB  = os.getenv("USE_STUB", "true").lower() == "true"
WS_PORT   = int(os.getenv("ASR_WS_PORT", "8765"))
VOCAB_PATH = Path(__file__).parents[2] / "shared/vocab/uz_banking_terms.json"

# ────────────────────────────────────────────────────────────────────────────
# Real model loading (skipped in stub mode)
# ────────────────────────────────────────────────────────────────────────────
whisper_model = None
diarization_pipeline = None
vad_model = None

def load_models():
    global whisper_model, diarization_pipeline, vad_model
    from faster_whisper import WhisperModel
    logger.info("Loading Whisper large-v3 INT8 …")
    whisper_model = WhisperModel("large-v3", device="cpu", compute_type="int8")

    logger.info("Loading pyannote diarization …")
    from pyannote.audio import Pipeline
    hf_token = os.environ["HF_TOKEN"]
    diarization_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", use_auth_token=hf_token
    )

    logger.info("Loading Silero VAD …")
    import torch
    vad_model, _ = torch.hub.load(
        repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False
    )
    logger.success("All models loaded")


# ────────────────────────────────────────────────────────────────────────────
# Vocabulary bias injection
# ────────────────────────────────────────────────────────────────────────────
def load_vocab_bias() -> list[str]:
    with open(VOCAB_PATH) as f:
        data = json.load(f)
    return data["banking_terms"]


# ────────────────────────────────────────────────────────────────────────────
# Code-switch boundary detector
# ────────────────────────────────────────────────────────────────────────────
import math

def detect_switch_boundary(tokens, threshold: float = 2.1) -> list[int]:
    """Return indices where language switches (entropy spike)."""
    boundaries = []
    for i, token in enumerate(tokens):
        if hasattr(token, 'probs') and token.probs:
            entropy = -sum(p * math.log(p + 1e-9) for p in token.probs)
            if entropy > threshold:
                boundaries.append(i)
    return boundaries


def classify_lang(text: str) -> str:
    """Heuristic: if both Cyrillic and Latin chars present → mixed."""
    has_latin   = any(c.isalpha() and ord(c) < 128 for c in text)
    has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
    if has_latin and has_cyrillic:
        return "mixed"
    return "ru" if has_cyrillic else "uz"


# ────────────────────────────────────────────────────────────────────────────
# STUB: fake transcript generator
# ────────────────────────────────────────────────────────────────────────────
STUB_LINES = [
    ("customer", "uz", "Assalomu alaykum, kredit karta haqida so'ramoqchi edim"),
    ("operator", "uz", "Albatta, sizga yordam beraman. Qanday miqdorni xohlaysiz?"),
    ("customer", "ru", "Мне интересно, какой у вас процент по карте?"),
    ("operator", "uz", "Bizda 12 oyga nol foiz taklif bor, limit 15 million so'm"),
    ("customer", "uz", "Foiz juda yuqori emas-mi? Menga o'ylash kerak"),
    ("operator", "uz", "Tushunaman, bu ajoyib taklif, ko'p mijozlar mamnun"),
]

async def stub_emitter(websocket, call_id: str):
    """Emit fake TranscriptWord events every ~1.5 seconds."""
    t = 0.0
    idx = 0
    while True:
        speaker, lang, text = STUB_LINES[idx % len(STUB_LINES)]
        words = text.split()
        chunk_words = []
        for w in words:
            word = TranscriptWord(
                ts_start=t, ts_end=t + 0.4,
                speaker=speaker, text=w, lang=lang,
                confidence=round(random.uniform(0.82, 0.99), 2)
            )
            chunk_words.append(word)
            t += 0.42
        chunk = TranscriptChunk(call_id=call_id, words=chunk_words)
        msg = {"type": "transcript_chunk", "payload": [w.dict() for w in chunk.words]}
        await websocket.send(json.dumps(msg))
        logger.debug(f"[STUB] Sent {len(chunk_words)} words → {text[:40]}")
        idx += 1
        await asyncio.sleep(1.5)


# ────────────────────────────────────────────────────────────────────────────
# REAL pipeline emitter (USE_STUB=false)
# ────────────────────────────────────────────────────────────────────────────
async def real_emitter(websocket, call_id: str):
    """Capture mic audio, run Whisper + pyannote, emit TranscriptWord events."""
    import sounddevice as sd
    import numpy as np

    SAMPLE_RATE = 16_000
    CHUNK_SEC   = 3          # process 3-second windows
    CHUNK_SAMP  = SAMPLE_RATE * CHUNK_SEC

    vocab_bias = load_vocab_bias()
    t = 0.0

    logger.info(f"[REAL] Starting audio capture @ {SAMPLE_RATE}Hz")
    while True:
        # Capture one chunk of audio
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,
            lambda: sd.rec(CHUNK_SAMP, samplerate=SAMPLE_RATE, channels=1,
                           dtype="float32", blocking=True).flatten()
        )

        # VAD gate — skip silence
        vad_out = vad_model({"waveform": __import__("torch").tensor(audio).unsqueeze(0),
                             "sample_rate": SAMPLE_RATE})
        if not list(vad_out.get_timeline()):
            await asyncio.sleep(0)
            continue

        # Whisper transcription (with vocab bias via initial_prompt)
        segments, _ = whisper_model.transcribe(
            audio,
            beam_size=5,
            initial_prompt=", ".join(vocab_bias[:30]),
            language=None,   # auto-detect uz/ru
        )
        segments = list(segments)
        if not segments:
            continue

        chunk_words = []
        for seg in segments:
            lang = classify_lang(seg.text)
            for word in (seg.words or []):
                tw = TranscriptWord(
                    ts_start=t + word.start,
                    ts_end=t + word.end,
                    speaker="unknown",      # diarization mapped below
                    text=word.word.strip(),
                    lang=lang,
                    confidence=round(getattr(word, "probability", 0.9), 2),
                )
                chunk_words.append(tw)

        # Diarization: map speaker labels to operator/customer
        import io, soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, audio, SAMPLE_RATE, format="WAV")
        buf.seek(0)
        diarization = diarization_pipeline(buf)
        speaker_map: dict[str, str] = {}
        for turn, _, label in diarization.itertracks(yield_label=True):
            if label not in speaker_map:
                role = "operator" if len(speaker_map) == 0 else "customer"
                speaker_map[label] = role
            for tw in chunk_words:
                if turn.start <= tw.ts_start <= turn.end:
                    tw.speaker = speaker_map[label]

        if chunk_words:
            msg = {"type": "transcript_chunk",
                   "payload": [w.dict() for w in chunk_words]}
            await websocket.send(json.dumps(msg))
            logger.debug(f"[REAL] Emitted {len(chunk_words)} words")

        t += CHUNK_SEC
        await asyncio.sleep(0)


# ────────────────────────────────────────────────────────────────────────────
# WebSocket handler
# ────────────────────────────────────────────────────────────────────────────
connected_clients: set = set()

async def handler(websocket):
    call_id = str(uuid.uuid4())
    connected_clients.add(websocket)
    logger.info(f"Client connected. call_id={call_id}. Total={len(connected_clients)}")
    try:
        # Send call_start event
        await websocket.send(json.dumps({"type": "call_start", "payload": {"call_id": call_id}}))
        if USE_STUB:
            await stub_emitter(websocket, call_id)
        else:
            await real_emitter(websocket, call_id)
    except websockets.ConnectionClosed:
        logger.info(f"Client disconnected. call_id={call_id}")
    finally:
        connected_clients.discard(websocket)


async def main():
    if not USE_STUB:
        load_models()
    logger.info(f"ASR WebSocket server starting on ws://0.0.0.0:{WS_PORT}  [stub={USE_STUB}]")
    async with websockets.serve(handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
