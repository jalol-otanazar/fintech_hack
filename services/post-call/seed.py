"""services/post-call/seed.py — Generate 1000 realistic demo call records."""
import asyncio, random, uuid
from datetime import datetime, timedelta
import asyncpg, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bankcopilot:bankcopilot@localhost:5432/bankcopilot")

OPERATORS = [
    ("Dilnoza Rahimova",   "Chilonzor filiali"),
    ("Jasur Karimov",      "Yunusobod filiali"),
    ("Malika Tosheva",     "Mirzo Ulug'bek filiali"),
    ("Bobur Yusupov",      "Sergeli filiali"),
    ("Zulfiya Ergasheva",  "Bosh ofis"),
]
OUTCOMES   = ["accepted", "interested", "rejected", "escalated"]
OUTCOME_W  = [0.30, 0.35, 0.28, 0.07]
PRODUCTS   = ["Kredit karta", "Muddatli depozit", "Talaba karta", "Ipoteka", None]
PERSONAS   = ["formal", "casual", "analytical", "emotional"]

def rand_call(op_id: int, op_branch: str) -> dict:
    duration  = random.randint(90, 600)
    kyc_done  = random.randint(3, 8)
    guardrail = random.choices([0, 1, 2], weights=[0.70, 0.22, 0.08])[0]
    outcome   = random.choices(OUTCOMES, weights=OUTCOME_W)[0]
    offer     = random.choice(PRODUCTS)

    kyc_pct   = kyc_done / 8
    offer_map = {"accepted": 30, "interested": 15, "rejected": 0, "escalated": 0}
    eff       = min(240 / duration, 1.0)
    quality   = round(
        kyc_pct * 40 + offer_map[outcome] + max(0, 20 - guardrail * 5) + eff * 10, 1
    )
    started   = datetime.utcnow() - timedelta(
        days=random.randint(0, 90), hours=random.randint(0, 8), minutes=random.randint(0, 59))

    return {
        "id":               str(uuid.uuid4()),
        "operator_id":      op_id,
        "customer_anon_id": f"Anon-{uuid.uuid4().hex[:8]}",
        "branch_name":      op_branch,
        "started_at":       started,
        "ended_at":         started + timedelta(seconds=duration),
        "duration_seconds": duration,
        "outcome":          outcome,
        "offer_name":       offer,
        "persona":          random.choice(PERSONAS),
        "quality_score":    quality,
        "kyc_done":         kyc_done,
        "kyc_total":        8,
        "guardrail_count":  guardrail,
        "summary_text":     f"Mijoz {offer or 'mahsulot'} haqida so'radi. Natija: {outcome}.",
    }


async def seed():
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)
    op_ids = []
    async with pool.acquire() as conn:
        for name, branch in OPERATORS:
            row = await conn.fetchrow(
                "INSERT INTO operators (name, branch_name) VALUES ($1,$2) "
                "ON CONFLICT DO NOTHING RETURNING id", name, branch)
            if row:
                op_ids.append((row["id"], branch))
            else:
                r2 = await conn.fetchrow("SELECT id FROM operators WHERE name=$1", name)
                op_ids.append((r2["id"], branch))

    print(f"Operators seeded: {len(op_ids)}")

    calls = []
    for i in range(1000):
        op_id, branch = random.choice(op_ids)
        calls.append(rand_call(op_id, branch))

    async with pool.acquire() as conn:
        await conn.executemany("""
            INSERT INTO calls (id, operator_id, customer_anon_id, branch_name,
                started_at, ended_at, duration_seconds, outcome, offer_name,
                persona, quality_score, kyc_done, kyc_total, guardrail_count, summary_text)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
            ON CONFLICT DO NOTHING
        """, [(c["id"], c["operator_id"], c["customer_anon_id"], c["branch_name"],
               c["started_at"], c["ended_at"], c["duration_seconds"], c["outcome"],
               c["offer_name"], c["persona"], c["quality_score"], c["kyc_done"],
               c["kyc_total"], c["guardrail_count"], c["summary_text"]) for c in calls])

    print(f"Seeded {len(calls)} calls ✅")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(seed())
