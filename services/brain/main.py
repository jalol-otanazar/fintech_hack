"""
services/brain/main.py
Decision layer: transcript stream → TurnContext → ActionCard.
Connects to ASR WebSocket, runs analysis, broadcasts to UI WebSocket.
"""
import asyncio, json, os, sys, time
from pathlib import Path
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger

sys.path.insert(0, str(Path(__file__).parents[2]))
from shared.types.models import (
    TranscriptWord, TurnContext, ActionCard, KycState,
    GuardrailAlert, KYC_ITEMS, CustomerProfile,
)
from services.brain.momentum import MomentumCalculator
from services.brain.persona import PersonaClassifier
from services.brain.nbo import NBOEngine
from services.brain.kyc import KycStateMachine
from services.brain.guardrail import GuardrailChecker
from services.brain.stress import StressDetector
from services.brain.claude_nlu import extract_turn_context

ASR_WS_URL  = os.getenv("ASR_WS_URL", "ws://localhost:8765")
BRAIN_PORT  = int(os.getenv("BRAIN_PORT", "8001"))

app = FastAPI(title="BankCopilot Brain")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Active sessions: call_id → state
sessions: dict[str, dict] = {}
# UI WebSocket clients: call_id → set of websockets
ui_clients: dict[str, set] = {}

_post_call_dir = str(Path(__file__).parents[1] / "post-call")
if _post_call_dir not in sys.path:
    sys.path.insert(0, _post_call_dir)
from crm_adapter import get_adapter as _get_crm_adapter
_crm_adapter = _get_crm_adapter()


# ─── UI WebSocket endpoint ──────────────────────────────────────────────────

@app.websocket("/ws/{call_id}")
async def ui_ws(websocket: WebSocket, call_id: str):
    await websocket.accept()
    ui_clients.setdefault(call_id, set()).add(websocket)
    logger.info(f"UI connected for call_id={call_id}")
    try:
        while True:
            await websocket.receive_text()   # keep-alive pings
    except WebSocketDisconnect:
        ui_clients.get(call_id, set()).discard(websocket)


async def broadcast(call_id: str, message: dict):
    clients = ui_clients.get(call_id, set()).copy()
    for ws in clients:
        try:
            await ws.send_json(message)
        except Exception:
            ui_clients.get(call_id, set()).discard(ws)


# ─── REST health ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "sessions": len(sessions)}


# ─── ASR consumer loop ──────────────────────────────────────────────────────

async def consume_asr():
    """Connect to ASR WebSocket, process chunks, broadcast to UI."""
    while True:
        try:
            async with websockets.connect(ASR_WS_URL) as ws:
                logger.info(f"Connected to ASR at {ASR_WS_URL}")
                async for raw in ws:
                    msg = json.loads(raw)
                    await handle_asr_message(msg)
        except Exception as e:
            logger.warning(f"ASR connection lost: {e}. Reconnecting in 2s …")
            await asyncio.sleep(2)


async def _fetch_and_store_profile(call_id: str, customer_id: str, session: dict) -> None:
    try:
        loop = asyncio.get_event_loop()
        profile = await loop.run_in_executor(None, _crm_adapter.fetch_profile, customer_id)
        session["customer_profile"] = profile
        if profile:
            logger.info(
                f"[{call_id[:8]}] CRM profile: tier={profile.risk_tier} "
                f"income={profile.income_bracket} owned={profile.owned_products}"
            )
    except Exception as e:
        logger.warning(f"[{call_id[:8]}] CRM fetch failed: {e}")
        session["customer_profile"] = None


async def handle_asr_message(msg: dict):
    mtype = msg.get("type")

    if mtype == "call_start":
        call_id     = msg["payload"]["call_id"]
        customer_id = msg["payload"].get("customer_id")
        sessions[call_id] = {
            "call_id":          call_id,
            "history":          [],
            "kyc":              KycState(call_id=call_id),
            "momentum":         MomentumCalculator(),
            "persona":          PersonaClassifier(),
            "nbo":              NBOEngine(),
            "guardrail":        GuardrailChecker(),
            "stress":           StressDetector(),
            "turn_num":         0,
            "customer_profile": None,
        }
        logger.info(f"New call session: {call_id}  customer_id={customer_id}")
        if customer_id:
            asyncio.create_task(_fetch_and_store_profile(call_id, customer_id, sessions[call_id]))

    elif mtype == "transcript_chunk":
        # Find active session (single-call stub: use first session)
        if not sessions:
            return
        call_id = next(iter(sessions))
        session = sessions[call_id]
        words = [TranscriptWord(**w) for w in msg["payload"]]
        session["history"].extend(words)
        session["turn_num"] += 1

        # Process only every 3rd chunk to avoid flooding Claude API
        if session["turn_num"] % 3 != 0:
            return

        await process_turn(call_id, session, words)


async def process_turn(call_id: str, session: dict, words: list[TranscriptWord]):
    """Core brain logic: extract context → score → decide → broadcast."""
    text = " ".join(w.text for w in words)
    speaker = words[0].speaker if words else "customer"

    # 1. NLU: extract TurnContext via Claude API
    ctx: TurnContext = await extract_turn_context(call_id, session["history"][-30:])

    # 2. Momentum — pass entities + question flag so all 4 components contribute
    is_question = any(w.text.endswith("?") for w in words)
    momentum = session["momentum"].update(
        ctx.sentiment,
        entities=ctx.entities if ctx.entities else None,
        is_question=is_question,
        expected_duration=120.0,  # demo call ~2 min
    )
    ctx.momentum = momentum

    # 3. Persona (classify once in first 10 turns)
    if session["turn_num"] <= 10:
        persona = session["persona"].classify(session["history"])
        ctx.persona = persona

    # 4. KYC transitions
    kyc: KycState = session["kyc"]
    session["guardrail"].check_kyc(kyc, text)
    kyc_dict = kyc.items.copy()

    # 5. Guardrail (operator speech only)
    guardrail_alert = None
    if speaker == "operator":
        alert = session["guardrail"].check(call_id, ctx.turn_id, text)
        if alert:
            guardrail_alert = alert
            await broadcast(call_id, {"type": "guardrail_alert", "payload": alert.dict()})

    # 6. Stress detector
    if speaker == "operator":
        stressed = session["stress"].check(words)
        if stressed:
            ctx.stress_detected = True
            await broadcast(call_id, {"type": "operator_stress", "payload": {"call_id": call_id}})

    # 7. NBO decision
    nbo: ActionCard | None = None
    if momentum >= 0.70 and speaker == "customer":
        nbo = session["nbo"].decide(ctx, profile=session.get("customer_profile"))
        ctx.nbo = nbo   # type: ignore[assignment]

    # 8. Broadcast TurnContext to UI
    payload = ctx.dict()
    payload["kyc"] = kyc_dict
    await broadcast(call_id, {"type": "turn_context", "payload": payload})
    logger.debug(f"[{call_id[:8]}] momentum={momentum:.2f} persona={ctx.persona} intent={ctx.intent}")


@app.on_event("startup")
async def startup():
    asyncio.create_task(consume_asr())


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=BRAIN_PORT, reload=False)
