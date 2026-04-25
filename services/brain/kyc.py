"""services/brain/kyc.py — KYC state machine."""
import re
from shared.types.models import KycState

KEYWORD_MAP = {
    "identity_confirmed":      [r"\bpassport\b", r"\bID\b", r"\bguvohnoma\b", r"\bshaxs\b"],
    "purpose_of_funds":        [r"\bmaqsad\b", r"\bnima uchun\b", r"\bцель\b", r"\bназначение\b"],
    "source_of_income":        [r"\bdaromad\b", r"\bish haqi\b", r"\bзарплата\b", r"\bдоход\b"],
    "pep_screening":           [r"\bPEP\b", r"\bsiyosiy\b", r"\bполитик\b"],
    "aml_acknowledgment":      [r"\bAML\b", r"\byuvish\b", r"\bотмыван\b"],
    "product_terms_explained": [r"\bshartlar\b", r"\bfoiz\b", r"\bпроцент\b", r"\bусловия\b"],
    "consent_recorded":        [r"\brozilik\b", r"\bruxsat\b", r"\bсогласие\b", r"\bсогласен\b"],
    "next_steps_communicated": [r"\bkeyingi\b", r"\bqadam\b", r"\bследующий\b", r"\bшаг\b"],
}

class GuardrailChecker:  # combined in one file for simplicity
    pass

class KycStateMachine:
    @classmethod
    def initial_state(cls, call_id: str = "default") -> KycState:
        return KycState(call_id=call_id)

    def advance(self, state: KycState, text: str, speaker: str) -> list[str]:
        """Check text for KYC keyword hits. Returns list of newly detected items."""
        newly_detected = []
        lower = text.lower()
        for item, patterns in KEYWORD_MAP.items():
            if state.items[item] == "PENDING":
                if any(re.search(p, lower, re.I) for p in patterns):
                    state.items[item] = "DETECTED"
                    newly_detected.append(item)
            elif state.items[item] == "DETECTED" and speaker == "operator":
                # Operator verbal confirmation
                if any(kw in lower for kw in ("ha", "tasdiqlandi", "да", "подтверждено", "ok", "✓")):
                    state.items[item] = "CONFIRMED"
        return newly_detected
