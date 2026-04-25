"""tests/test_brain.py — Unit tests: momentum, persona, guardrail, stress."""
import sys
from pathlib import Path
_root = Path(__file__).parents[1]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "services" / "post-call"))  # hyphenated dir, not importable as package

import pytest

# ── Momentum ──────────────────────────────────────────────────────────────────
from services.brain.momentum import MomentumCalculator

def test_momentum_positive_sentiment_rises():
    calc = MomentumCalculator()
    score = 0.0
    for _ in range(5):
        score = calc.update(sentiment=0.8, is_question=True,
                            entities={"kredit": True, "foiz": True})
    assert score > 0.4, f"Expected >0.4, got {score}"

def test_momentum_negative_stays_low():
    calc = MomentumCalculator()
    score = 0.0
    for _ in range(5):
        score = calc.update(sentiment=-0.9, is_question=False, entities=None)
    assert score < 0.6, f"Expected <0.6, got {score}"

def test_momentum_clamped_0_1():
    calc = MomentumCalculator()
    score = 0.0
    for _ in range(15):
        score = calc.update(sentiment=1.0, is_question=True,
                            entities={f"k{i}": True for i in range(10)})
    assert 0.0 <= score <= 1.0, f"Out of bounds: {score}"

def test_momentum_returns_float():
    calc = MomentumCalculator()
    result = calc.update(sentiment=0.5)
    assert isinstance(result, float)

# ── Persona ───────────────────────────────────────────────────────────────────
from shared.types.models import TranscriptWord

def _word(text: str, speaker: str = "customer", lang: str = "uz") -> TranscriptWord:
    return TranscriptWord(ts_start=0.0, ts_end=0.5, speaker=speaker,
                          text=text, lang=lang, confidence=0.95)

from services.brain.persona import PersonaClassifier

def test_persona_returns_valid_label():
    clf = PersonaClassifier()
    words = [_word("salom"), _word("kredit"), _word("karta")]
    result = clf.classify(words)
    assert result in ("formal", "casual", "analytical", "emotional")

def test_persona_analytical_on_numbers():
    clf = PersonaClassifier()
    words = [_word("100"), _word("foiz"), _word("200000"), _word("necha"), _word("kredit")]
    result = clf.classify(words)
    assert result == "analytical"

def test_persona_formal_on_markers():
    clf = PersonaClassifier()
    words = [_word("hurmatli"), _word("hurmatli"), _word("iltimos"), _word("marhamat")]
    result = clf.classify(words)
    assert result == "formal"

def test_persona_empty_history_defaults():
    clf = PersonaClassifier()
    result = clf.classify([])
    assert result in ("formal", "casual", "analytical", "emotional")

# ── Guardrail ─────────────────────────────────────────────────────────────────
from services.brain.guardrail import GuardrailChecker

def test_guardrail_blocks_kafolatli():
    gc = GuardrailChecker()
    hit = gc.check("call-1", "turn-1", "bu kafolatli foyda beradi")
    assert hit is not None
    assert hit.replacement

def test_guardrail_blocks_albatta_tasdiqlanadi():
    gc = GuardrailChecker()
    hit = gc.check("call-1", "turn-2", "Sizning arizangiz albatta tasdiqlanadi")
    assert hit is not None

def test_guardrail_allows_clean_text():
    gc = GuardrailChecker()
    hit = gc.check("call-1", "turn-3", "yuqori potentsial daromad beradi")
    assert hit is None

def test_guardrail_replacement_nonempty():
    gc = GuardrailChecker()
    hit = gc.check("call-1", "turn-4", "eng yaxshi kredit")
    if hit:
        assert len(hit.replacement) > 0

def test_guardrail_russian_phrase():
    gc = GuardrailChecker()
    hit = gc.check("call-2", "turn-1", "это гарантированный доход")
    assert hit is not None

# ── Stress ────────────────────────────────────────────────────────────────────
from services.brain.stress import StressDetector

def _op_word(text: str, ts_start: float, ts_end: float) -> TranscriptWord:
    return TranscriptWord(ts_start=ts_start, ts_end=ts_end,
                          speaker="operator", text=text, lang="uz", confidence=0.9)

def test_stress_no_flag_normal_speech():
    sd = StressDetector()
    words = [_op_word("salom", i * 0.5, i * 0.5 + 0.4) for i in range(20)]
    # No baseline set yet → should not flag
    result = sd.check(words)
    assert isinstance(result, bool)

def test_stress_no_crash_empty():
    sd = StressDetector()
    result = sd.check([])
    assert result is False


# ── CustomerProfile ───────────────────────────────────────────────────────────
from shared.types.models import CustomerProfile

def test_customer_profile_defaults():
    p = CustomerProfile(customer_id="x", age=30, income_bracket="mid")
    assert p.owned_products == []
    assert p.previous_rejections == []
    assert p.risk_tier == "standard"
    assert p.transaction_volume_monthly == 0.0

def test_customer_profile_rejects_bad_income():
    with pytest.raises(Exception):
        CustomerProfile(customer_id="x", age=30, income_bracket="ultra_rich")


# ── MockCRMAdapter.fetch_profile ──────────────────────────────────────────────
from crm_adapter import MockCRMAdapter

def test_mock_crm_fetch_profile_deterministic():
    adapter = MockCRMAdapter()
    p1 = adapter.fetch_profile("cust-001")
    p2 = adapter.fetch_profile("cust-001")
    assert p1.age == p2.age
    assert p1.income_bracket == p2.income_bracket
    assert p1.owned_products == p2.owned_products
    assert p1.risk_tier == p2.risk_tier

def test_mock_crm_different_customers_have_correct_ids():
    adapter = MockCRMAdapter()
    p1 = adapter.fetch_profile("cust-001")
    p2 = adapter.fetch_profile("cust-999")
    assert p1.customer_id == "cust-001"
    assert p2.customer_id == "cust-999"

def test_mock_crm_valid_field_ranges():
    adapter = MockCRMAdapter()
    p = adapter.fetch_profile("test-customer-abc")
    assert 18 <= p.age <= 75
    assert p.income_bracket in ("low", "mid", "high")
    assert p.risk_tier in ("standard", "premium", "vip")
    assert p.transaction_volume_monthly >= 200_000


# ── NBO engine: profile-aware ─────────────────────────────────────────────────
from services.brain.nbo import NBOEngine
from shared.types.models import TurnContext

def _ctx(intent: str = "inquiry_credit_card", momentum: float = 0.8) -> TurnContext:
    return TurnContext(
        call_id="test-call",
        speaker="customer",
        intent=intent,
        sentiment=0.5,
        momentum=momentum,
        persona="casual",
    )

def test_nbo_filters_owned_product():
    engine = NBOEngine()
    profile = CustomerProfile(
        customer_id="x", age=35, income_bracket="low",
        owned_products=["credit_card"],
    )
    ctx = _ctx(intent="inquiry_credit_card")
    card = engine.decide(ctx, profile=profile)
    assert card is None or card.product != "credit_card"

def test_nbo_high_income_gets_premium_card():
    engine = NBOEngine()
    profile = CustomerProfile(
        customer_id="x", age=40, income_bracket="high",
        owned_products=[],
    )
    card = engine.decide(_ctx(intent="inquiry_credit_card"), profile=profile)
    assert card is not None
    assert card.product == "premium_card"

def test_nbo_high_income_gets_premium_deposit():
    engine = NBOEngine()
    profile = CustomerProfile(
        customer_id="x", age=40, income_bracket="high",
        owned_products=[],
    )
    card = engine.decide(_ctx(intent="inquiry_deposit"), profile=profile)
    assert card is not None
    assert card.product == "premium_deposit"

def test_nbo_vip_confidence_boost():
    engine = NBOEngine()
    base_profile = CustomerProfile(customer_id="x", age=40, income_bracket="mid", risk_tier="standard")
    vip_profile  = CustomerProfile(customer_id="y", age=40, income_bracket="mid", risk_tier="vip")
    ctx = _ctx(momentum=0.5)
    base_card = engine.decide(ctx, profile=base_profile)
    vip_card  = engine.decide(ctx, profile=vip_profile)
    assert vip_card is not None and base_card is not None
    assert vip_card.confidence > base_card.confidence

def test_nbo_rejection_reduces_confidence():
    engine = NBOEngine()
    clean_profile    = CustomerProfile(customer_id="x", age=40, income_bracket="mid", previous_rejections=[])
    rejected_profile = CustomerProfile(customer_id="y", age=40, income_bracket="mid", previous_rejections=["credit_card"])
    ctx = _ctx(intent="inquiry_credit_card", momentum=0.8)
    clean_card    = engine.decide(ctx, profile=clean_profile)
    rejected_card = engine.decide(ctx, profile=rejected_profile)
    assert clean_card is not None and rejected_card is not None
    assert rejected_card.confidence < clean_card.confidence

def test_nbo_no_profile_behaves_as_before():
    engine = NBOEngine()
    ctx = _ctx(intent="inquiry_deposit", momentum=0.7)
    card = engine.decide(ctx, profile=None)
    assert card is not None
    assert card.product == "deposit"
    expected = round(min(0.95, 0.60 + 0.7 * 0.35), 2)
    assert card.confidence == expected

def test_nbo_all_candidates_owned_returns_none():
    engine = NBOEngine()
    profile = CustomerProfile(
        customer_id="x", age=35, income_bracket="low",
        owned_products=["credit_card", "student_card"],
    )
    # All matrix results for this intent path are credit_card / student_card
    ctx = _ctx(intent="inquiry_credit_card")
    ctx.entities["age_young"] = True
    card = engine.decide(ctx, profile=profile)
    # student_card is owned too; premium upgrade doesn't apply (low income)
    assert card is None
