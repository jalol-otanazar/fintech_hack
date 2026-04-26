"""
services/asr/main.py
Real-time Uzbek/Russian ASR using Groq Whisper API + sounddevice mic capture.
Emits TranscriptWord events via WebSocket.

Phase 0: stub mode (USE_STUB=true) emits fake events.
Phase 1: real mode — mic → Groq Whisper API → TranscriptWord stream.
"""
import asyncio, json, os, sys, io, math, random, uuid
from pathlib import Path
import websockets
from loguru import logger

# ── path: works in Docker (/app) and local dev (services/asr → project root)
_here = Path(__file__).resolve().parent
_root = _here.parents[1] if len(_here.parents) > 1 else _here
sys.path.insert(0, str(_here))
sys.path.insert(0, str(_root))
from shared.types.models import TranscriptWord, TranscriptChunk

USE_STUB  = os.getenv("USE_STUB", "true").lower() == "true"
WS_PORT   = int(os.getenv("ASR_WS_PORT", "8765"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
VOCAB_PATH = _root / "shared/vocab/uz_banking_terms.json"


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────
def classify_lang(text: str) -> str:
    """Heuristic: Cyrillic → ru, Latin → uz, both → mixed."""
    has_latin    = any(c.isalpha() and ord(c) < 128 for c in text)
    has_cyrillic = any('Ѐ' <= c <= 'ӿ' for c in text)
    if has_latin and has_cyrillic:
        return "mixed"
    return "ru" if has_cyrillic else "uz"


def load_vocab_bias() -> list[str]:
    try:
        with open(VOCAB_PATH) as f:
            return json.load(f)["banking_terms"]
    except Exception:
        return []


# ────────────────────────────────────────────────────────────────────────────
# STUB: fake transcript generator
# ────────────────────────────────────────────────────────────────────────────
STUB_LINES = [
    ("customer", "uz", "Assalomu alaykum, kredit karta olish haqida so'ramoqchi edim"),
    ("operator", "uz", "Xush kelibsiz! Avval shaxsingizni tasdiqlaylik — guvohnoma raqamingizni ayta olasizmi?"),
    ("customer", "uz", "Ha, shaxsim tasdiqlangan, guvohnomam bor. Maqsadim — xarid va online to'lovlar"),
    ("operator", "uz", "Rahmat! Oylik daromadingiz qancha va ish joyingiz rasmiy?"),
    ("customer", "uz", "Ha, rasmiy ishda ishlaman. Oylik maoshim 12 million so'm, IT sektorida"),
    ("operator", "uz", "Ajoyib! Platinum kartamizning shartlari: 24 oyga foiz 0%, limit 30 million so'm, cashback 3%"),
    ("customer", "uz", "Voy, 30 million so'm limit? Bu menga juda mos! Yillik to'lov bormi?"),
    ("operator", "uz", "Bu eng yaxshi mahsulot bizda, albatta tasdiqlanadi arizangiz, hujjat minimal"),
    ("customer", "ru", "Звучит отлично! Мне очень нравится. А cashback на все покупки распространяется?"),
    ("operator", "uz", "Ha, barcha xaridlarda 3% cashback, airport lounge kirish ham bepul!"),
    ("operator", "uz", "Standart savol: siyosiy shaxs yoki PEP maqomingiz bormi? AML tekshiruv kerak"),
    ("customer", "uz", "Yo'q, PEP emasman, xususiy sektor xodimiman. AML talablarini tushunaman"),
    ("customer", "uz", "12 million so'm daromadim bilan bu platinum karta to'g'ri tanlov, qachon tayyor bo'ladi?"),
    ("operator", "uz", "2 ish kunida tayyor! Siz uchun premium mijoz sifatida tezlashtirilgan ko'rib chiqish"),
    ("customer", "uz", "Juda yaxshi, bu taklifni qabul qilmoqchiman! Hoziroq rasmiylashtirsak bo'ladimi?"),
    ("customer", "ru", "Я очень доволен условиями, оформляйте пожалуйста"),
    ("operator", "uz", "Ajoyib qaror! Sizning roziligingizni qayd etamiz. Ruxsat bersangiz ariza rasmiylashtiriladi"),
    ("customer", "uz", "Ha, roziman va to'liq ruxsat beraman. Imzolashga tayyorman"),
    ("operator", "uz", "Keyingi qadam: passport skaneri, keyin 2 kun ichida karta uyingizga yetkaziladi"),
    ("customer", "uz", "Rahmat, juda professional xizmat! Do'stlarimga ham tavsiya qilaman"),
    ("customer", "ru", "Спасибо большое, очень доволен! Отличный банк"),
    ("operator", "uz", "Sizga ham rahmat! Xush ko'rdik, yana murojaat qiling. Xayr!"),
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
        msg = {"type": "transcript_chunk", "payload": [w.dict() for w in chunk_words]}
        await websocket.send(json.dumps(msg))
        logger.debug(f"[STUB] Sent {len(chunk_words)} words → {text[:40]}")
        idx += 1
        await asyncio.sleep(1.5)


# ────────────────────────────────────────────────────────────────────────────
# REAL pipeline: mic → Groq Whisper API → TranscriptWord
# ────────────────────────────────────────────────────────────────────────────
async def real_emitter(websocket, call_id: str):
    """Capture mic in 3s chunks, transcribe via Groq Whisper, emit words."""
    import sounddevice as sd
    import numpy as np
    import soundfile as sf
    from groq import Groq

    SAMPLE_RATE = 16_000
    CHUNK_SEC   = 3
    CHUNK_SAMP  = SAMPLE_RATE * CHUNK_SEC

    groq_client = Groq(api_key=GROQ_API_KEY)
    vocab_bias  = load_vocab_bias()
    prompt_hint = "Uzbek and Russian bank call. Terms: " + ", ".join(vocab_bias[:20])

    # Simple speaker tracker: first distinct voice = operator, second = customer
    # We alternate per-chunk based on energy level comparison
    speaker_turn = 0          # 0 = operator, 1 = customer
    last_rms     = 0.0
    t            = 0.0

    logger.info(f"[REAL] Groq Whisper mode — mic capture @ {SAMPLE_RATE}Hz, {CHUNK_SEC}s chunks")

    while True:
        # 1. Capture audio chunk
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,
            lambda: sd.rec(CHUNK_SAMP, samplerate=SAMPLE_RATE, channels=1,
                           dtype="float32", blocking=True).flatten()
        )

        # 2. Skip silence (RMS < threshold)
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < 0.005:
            logger.debug(f"[REAL] Silence skipped (rms={rms:.4f})")
            t += CHUNK_SEC
            await asyncio.sleep(0)
            continue

        # 3. Simple speaker change detection: big RMS jump → new speaker
        if last_rms > 0 and rms > last_rms * 2.5:
            speaker_turn = 1 - speaker_turn   # flip
        last_rms = rms
        speaker = "operator" if speaker_turn == 0 else "customer"

        # 4. Encode to WAV bytes for Groq API
        buf = io.BytesIO()
        sf.write(buf, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        buf.seek(0)
        buf.name = "audio.wav"   # Groq needs a filename hint

        # 5. Groq Whisper transcription (async via executor)
        try:
            result = await loop.run_in_executor(
                None,
                lambda: groq_client.audio.transcriptions.create(
                    file=("audio.wav", buf.read(), "audio/wav"),
                    model="whisper-large-v3",
                    prompt=prompt_hint,
                    response_format="verbose_json",
                    language=None,     # auto-detect uz/ru
                )
            )
        except Exception as e:
            logger.warning(f"[REAL] Groq API error: {e}")
            t += CHUNK_SEC
            await asyncio.sleep(0)
            continue

        text = result.text.strip()
        if not text:
            t += CHUNK_SEC
            await asyncio.sleep(0)
            continue

        lang = classify_lang(text)
        logger.info(f"[REAL] [{speaker}] ({lang}) {text[:60]}")

        # 6. Build TranscriptWord list from Groq word timestamps (if available)
        chunk_words = []
        segments = getattr(result, "segments", None) or []
        if segments:
            for seg in segments:
                seg_lang = classify_lang(seg.get("text", text))
                for w in seg.get("words", []):
                    chunk_words.append(TranscriptWord(
                        ts_start=t + w.get("start", 0),
                        ts_end=t + w.get("end", 0),
                        speaker=speaker,
                        text=w.get("word", "").strip(),
                        lang=seg_lang,
                        confidence=round(w.get("probability", 0.9), 2),
                    ))
        else:
            # Fallback: split text into words with estimated timestamps
            words = text.split()
            dur_per_word = CHUNK_SEC / max(len(words), 1)
            for i, w in enumerate(words):
                chunk_words.append(TranscriptWord(
                    ts_start=t + i * dur_per_word,
                    ts_end=t + (i + 1) * dur_per_word,
                    speaker=speaker,
                    text=w,
                    lang=lang,
                    confidence=0.90,
                ))

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
    call_id = "demo-call-001" if USE_STUB else str(uuid.uuid4())
    connected_clients.add(websocket)
    logger.info(f"Client connected. call_id={call_id}. Total={len(connected_clients)}")
    try:
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
    if not USE_STUB and not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set! Set it in .env or environment.")
        return
    logger.info(f"ASR WebSocket server starting on ws://0.0.0.0:{WS_PORT}  [stub={USE_STUB}]")
    async with websockets.serve(handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
