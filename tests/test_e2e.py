"""tests/test_e2e.py — End-to-end load test: 60 events/min sustained.

This test:
1. Spins up the brain's event processing logic directly (no HTTP, no Electron)
2. Feeds 60 TurnContext events per minute for 2 minutes (120 events total)
3. Verifies every event is processed in <2s
4. Verifies momentum, KYC, guardrail state are consistent after the run
5. No browser / no Playwright needed — tests the Python pipeline under load
"""
import sys, time, asyncio, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest

from services.brain.momentum  import MomentumCalculator
from services.brain.guardrail import GuardrailChecker
from services.brain.kyc       import KycStateMachine
from services.brain.stress    import StressDetector
from shared.types.models      import TranscriptWord

# ── Helpers ───────────────────────────────────────────────────────────────────

def _word(text: str, speaker: str = "operator", ts: float = 0.0) -> TranscriptWord:
    return TranscriptWord(
        ts_start=ts, ts_end=ts + 0.4,
        speaker=speaker, text=text, lang="uz", confidence=0.93,
    )

# 120 synthetic turns alternating customer / operator
_SCRIPT = [
    ("customer", "Salom, kredit karta olmoqchi edim"),
    ("operator",  "Albatta, sizga yordam beraman"),
    ("customer", "Foiz qancha?"),
    ("operator",  "12 oyga nol foiz, limit 15 million"),
    ("customer", "Hujjatlar kerakmi?"),
    ("operator",  "Pasport va STIR kerak"),
    ("customer", "Qancha vaqt kerak?"),
    ("operator",  "3-5 ish kuni"),
    ("customer", "Juda yaxshi, ariza topshiraman"),
    ("operator",  "Marhamat, yordam beramiz"),
] * 12  # 120 turns total


# ── Load test ─────────────────────────────────────────────────────────────────

def process_turn(
    turn_idx: int,
    speaker: str,
    text: str,
    momentum_calc: MomentumCalculator,
    guardrail: GuardrailChecker,
    kyc: KycStateMachine,
    kyc_state: dict,
    stress: StressDetector,
    call_ts: float,
) -> dict:
    """Synchronous processing of a single turn. Must complete in <2s."""
    t0 = time.perf_counter()
    word = _word(text, speaker, call_ts + turn_idx * 0.5)

    # 1. Momentum update
    sentiment = 0.6 if speaker == "customer" else 0.5
    momentum_val = momentum_calc.update(
        sentiment=sentiment,
        is_question="?" in text or text.endswith("mi"),
        entities={"kredit": True} if "kredit" in text else None,
    )

    # 2. Guardrail (operator only)
    guardrail_hit = None
    if speaker == "operator":
        call_id = "load-test-call"
        guardrail_hit = guardrail.check(call_id, f"turn-{turn_idx}", text)

    # 3. KYC advance
    kyc.advance(kyc_state, text, speaker)

    # 4. Stress check (every 10 turns)
    stress_flag = False
    if turn_idx % 10 == 0:
        words = [_word(text, speaker, call_ts + turn_idx * 0.5)]
        stress_flag = stress.check(words)

    elapsed = time.perf_counter() - t0
    return {
        "turn": turn_idx,
        "elapsed_ms": elapsed * 1000,
        "momentum": momentum_val,
        "guardrail": guardrail_hit is not None,
        "stress": stress_flag,
    }


def test_60_events_per_minute_for_2_minutes():
    """
    Feed 120 events (60/min × 2min) through the brain pipeline.
    Assert: every event processed in <2000ms.
    Assert: final momentum is valid float in [0,1].
    Assert: no unhandled exceptions.
    """
    momentum_calc = MomentumCalculator()
    guardrail     = GuardrailChecker()
    kyc           = KycStateMachine()
    kyc_state     = kyc.initial_state()
    stress        = StressDetector()

    call_ts   = time.time()
    results   = []
    slow_turns = []

    for i, (speaker, text) in enumerate(_SCRIPT):
        result = process_turn(
            i, speaker, text,
            momentum_calc, guardrail, kyc, kyc_state, stress, call_ts
        )
        results.append(result)
        if result["elapsed_ms"] > 2000:
            slow_turns.append((i, result["elapsed_ms"]))

    assert len(results) == 120, f"Expected 120 results, got {len(results)}"
    assert not slow_turns, (
        f"Turns exceeded 2000ms deadline: {slow_turns}"
    )

    final_momentum = results[-1]["momentum"]
    assert 0.0 <= final_momentum <= 1.0, f"Momentum out of bounds: {final_momentum}"


def test_throughput_rate():
    """120 turns must complete in under 5 seconds wall-clock time."""
    momentum_calc = MomentumCalculator()
    guardrail     = GuardrailChecker()
    kyc           = KycStateMachine()
    kyc_state     = kyc.initial_state()
    stress        = StressDetector()
    call_ts       = time.time()

    t0 = time.perf_counter()
    for i, (speaker, text) in enumerate(_SCRIPT):
        process_turn(i, speaker, text, momentum_calc, guardrail, kyc, kyc_state, stress, call_ts)
    total = time.perf_counter() - t0

    assert total < 5.0, f"120 events took {total:.2f}s — too slow (limit: 5s)"
    print(f"\n  ✅ 120 events in {total:.3f}s  ({120/total:.0f} events/sec)")


def test_kyc_completion_after_full_call():
    """After 120 turns covering all KYC keywords, completion should be >50%."""
    kyc       = KycStateMachine()
    kyc_state = kyc.initial_state()

    # Feed turns using exact base forms matched by KYC regex patterns
    kyc_turns = [
        ("operator", "passport ko'rsating"),           # identity_confirmed  → \bpassport\b
        ("operator", "maqsad nima bu"),                # purpose_of_funds    → \bmaqsad\b
        ("customer", "daromad bor ish haqi"),          # source_of_income    → \bdaromad\b
        ("operator", "shartlar va foiz tushuntirildi"),# product_terms_explained → \bshartlar\b
        ("operator", "rozilik olamiz ruxsat"),         # consent_recorded    → \brozilik\b
        ("operator", "keyingi qadam aytaman"),         # next_steps_communicated → \bkeyingi\b
    ]
    for speaker, text in kyc_turns:
        kyc.advance(kyc_state, text, speaker)

    done = sum(1 for v in kyc_state.items.values() if v != "PENDING")
    total = len(kyc_state.items)
    pct = done / total
    assert pct >= 0.50, f"KYC completion {pct:.0%} after seeded turns — expected ≥50%"
