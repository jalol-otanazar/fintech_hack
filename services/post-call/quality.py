"""services/post-call/quality.py — Deterministic quality scorer (no LLM)."""
from shared.types.models import CallSummary


def compute_quality_score(summary: CallSummary) -> dict:
    """
    Returns detailed breakdown + total (0–100).

    Formula:
      kyc_completeness_pct   × 40
      offer_conversion_hit   × 30   (accepted=30, interested=15, rejected/escalated=0)
      guardrail_clean        × 20   (clean=20, minus 5 per fire, floor 0)
      call_efficiency        × 10   (expected_duration / actual, clamped 0–1)
    """
    expected_duration = 240  # seconds — benchmark for a well-paced call

    # Component 1: KYC
    kyc_pct = summary.kyc_done / max(summary.kyc_total, 1)
    kyc_score = round(kyc_pct * 40, 2)

    # Component 2: Offer outcome
    offer_map = {"accepted": 30, "interested": 15, "rejected": 0, "escalated": 0}
    offer_score = float(offer_map.get(summary.outcome, 0))

    # Component 3: Guardrail cleanliness
    guardrail_score = max(0.0, 20.0 - summary.guardrail_count * 5)

    # Component 4: Efficiency
    if summary.duration_seconds and summary.duration_seconds > 0:
        efficiency_ratio = min(expected_duration / summary.duration_seconds, 1.0)
    else:
        efficiency_ratio = 0.5
    efficiency_score = round(efficiency_ratio * 10, 2)

    total = round(kyc_score + offer_score + guardrail_score + efficiency_score, 2)

    return {
        "kyc_component":          kyc_score,
        "offer_component":        offer_score,
        "guardrail_component":    guardrail_score,
        "efficiency_component":   efficiency_score,
        "total":                  min(total, 100.0),
    }
