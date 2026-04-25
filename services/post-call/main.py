"""services/post-call/main.py
Post-call agent: listens for call_end events, generates Uzbek CRM summary
via Claude API, scores the call, writes to PostgreSQL, pushes to CRM.
"""
import asyncio, json, os, sys, uuid
from pathlib import Path
from datetime import datetime

import asyncpg
import websockets
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger
from anthropic import AsyncAnthropic

sys.path.insert(0, str(Path(__file__).parents[2]))
from shared.types.models import CallSummary
from services.post_call.quality import compute_quality_score
from services.post_call.crm_adapter import get_adapter

BRAIN_WS_URL = os.getenv("BRAIN_WS_URL", "ws://localhost:8001/ws/post-call-agent")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bankcopilot:bankcopilot@localhost:5432/bankcopilot")
POST_CALL_PORT = int(os.getenv("POST_CALL_PORT", "8002"))

anthropic = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
crm = get_adapter()

app = FastAPI(title="BankCopilot Post-Call")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

db_pool: asyncpg.Pool | None = None


# ── DB ───────────────────────────────────────────────────────────────────────

async def get_db():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return db_pool


async def save_call(pool, summary: CallSummary, score_breakdown: dict):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO calls (id, customer_anon_id, branch_name, started_at, ended_at,
                duration_seconds, outcome, offer_name, persona, quality_score,
                kyc_done, kyc_total, guardrail_count, summary_text)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
            ON CONFLICT (id) DO NOTHING
        """, summary.call_id, summary.customer_anon_id, summary.branch_name,
            summary.created_at, summary.created_at,
            summary.duration_seconds, summary.outcome, summary.offer_name,
            summary.persona, summary.quality_score,
            summary.kyc_done, summary.kyc_total, summary.guardrail_count, summary.summary_text)

        await conn.execute("""
            INSERT INTO quality_scores (call_id, kyc_component, offer_component,
                guardrail_component, efficiency_component, total)
            VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING
        """, summary.call_id,
            score_breakdown["kyc_component"], score_breakdown["offer_component"],
            score_breakdown["guardrail_component"], score_breakdown["efficiency_component"],
            score_breakdown["total"])


# ── Summary generator ────────────────────────────────────────────────────────

SUMMARY_SYSTEM = """Sen BankCopilot xulosa tizimisan. Qo'ng'iroq ma'lumotlari asosida 
qisqa, aniq Uzbek tilida CRM xulosasi yoz. Faqat JSON qaytarishingiz kerak, boshqa hech narsa yo'q.

JSON format:
{
  "detected_needs": ["list", "of", "needs"],
  "offer_name": "mahsulot nomi yoki null",
  "offer_details": "taklif tafsilotlari yoki null",
  "outcome": "accepted|interested|rejected|escalated",
  "next_step": "keyingi qadam",
  "summary_text": "2-3 jumla xulosasi Uzbek tilida"
}"""

async def generate_summary(call_id: str, transcript_words: list, metadata: dict) -> dict:
    transcript_text = "\n".join(
        f"[{w['speaker'].upper()}] ({w.get('lang','uz')}) {w['text']}"
        for w in transcript_words[-100:]  # last 100 words
    )
    user_msg = f"""Qo'ng'iroq ID: {call_id}
Operator: {metadata.get('operator_name', 'Noma\'lum')}
Davomiyligi: {metadata.get('duration_seconds', 0)} soniya
KYC bajarildi: {metadata.get('kyc_done', 0)}/8
Guardrail ogohlantirish: {metadata.get('guardrail_count', 0)}

Transkripsiya:
{transcript_text}

JSON xulosasi:"""

    try:
        resp = await anthropic.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SUMMARY_SYSTEM,
            messages=[{"role": "user", "content": user_msg}]
        )
        raw = resp.content[0].text.strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Claude summary failed: {e} — using stub")
        return {
            "detected_needs": ["kredit karta", "foiz so'rovi"],
            "offer_name": "Kredit karta",
            "offer_details": "12 oyga 0% foiz, 15M limit",
            "outcome": "interested",
            "next_step": "Ariza topshirish uchun filialga keling",
            "summary_text": f"Mijoz kredit karta haqida so'radi. Operator taklif qildi. Mijoz qiziqdi.",
        }


# ── call_end handler ──────────────────────────────────────────────────────────

async def handle_call_end(data: dict):
    call_id  = data["call_id"]
    words    = data.get("transcript", [])
    meta     = data.get("metadata", {})
    start_ts = datetime.utcnow()

    logger.info(f"[PostCall] Processing call_end for {call_id}")

    # 1. Generate summary via Claude
    result = await generate_summary(call_id, words, meta)

    # 2. Build CallSummary
    summary = CallSummary(
        call_id=call_id,
        operator_name=meta.get("operator_name", "Operator"),
        customer_anon_id=meta.get("customer_anon_id", f"Anon-{call_id[:8]}"),
        duration_seconds=meta.get("duration_seconds", 0),
        branch_name=meta.get("branch_name", "Bosh filial"),
        detected_needs=result.get("detected_needs", []),
        offer_name=result.get("offer_name"),
        offer_details=result.get("offer_details"),
        persona=meta.get("persona", "casual"),
        outcome=result.get("outcome", "rejected"),
        next_step=result.get("next_step", "—"),
        kyc_done=meta.get("kyc_done", 0),
        kyc_missing_items=meta.get("kyc_missing", []),
        guardrail_count=meta.get("guardrail_count", 0),
        quality_score=0.0,
        summary_text=result.get("summary_text", ""),
    )

    # 3. Quality score
    breakdown = compute_quality_score(summary)
    summary.quality_score = breakdown["total"]

    elapsed = (datetime.utcnow() - start_ts).total_seconds()
    logger.success(f"[PostCall] Summary done in {elapsed:.1f}s  score={summary.quality_score}")

    # 4. Persist to DB
    try:
        pool = await get_db()
        await save_call(pool, summary, breakdown)
    except Exception as e:
        logger.error(f"[PostCall] DB write failed: {e}")

    # 5. Push to CRM
    crm.push_summary(call_id, summary)
    return summary


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.post("/call-end")
async def call_end_endpoint(body: dict):
    summary = await handle_call_end(body)
    return {"status": "ok", "quality_score": summary.quality_score}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/calls")
async def list_calls(limit: int = 50, offset: int = 0):
    pool = await get_db()
    rows = await pool.fetch(
        "SELECT * FROM calls ORDER BY created_at DESC LIMIT $1 OFFSET $2", limit, offset)
    return [dict(r) for r in rows]

@app.get("/operators/stats")
async def operator_stats():
    pool = await get_db()
    rows = await pool.fetch("""
        SELECT o.name, o.branch_name,
               COUNT(c.id) AS total_calls,
               ROUND(AVG(c.quality_score)::numeric, 1) AS avg_quality,
               SUM(c.guardrail_count) AS total_guardrails,
               SUM(CASE WHEN c.outcome='accepted' THEN 1 ELSE 0 END) AS offers_accepted
        FROM operators o LEFT JOIN calls c ON c.operator_id = o.id
        GROUP BY o.id, o.name, o.branch_name ORDER BY avg_quality DESC NULLS LAST
    """)
    return [dict(r) for r in rows]

@app.get("/flagged")
async def flagged_calls():
    pool = await get_db()
    rows = await pool.fetch("""
        SELECT * FROM calls
        WHERE quality_score < 60 OR guardrail_count > 0
        ORDER BY created_at DESC LIMIT 100
    """)
    return [dict(r) for r in rows]

@app.get("/compliance")
async def compliance_log():
    pool = await get_db()
    rows = await pool.fetch(
        "SELECT * FROM guardrail_events ORDER BY fired_at DESC LIMIT 200")
    return [dict(r) for r in rows]


@app.on_event("startup")
async def startup():
    try:
        await get_db()
        logger.success("DB pool connected")
    except Exception as e:
        logger.warning(f"DB unavailable (demo mode): {e}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=POST_CALL_PORT, reload=False)
