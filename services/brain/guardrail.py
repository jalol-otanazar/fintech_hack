"""services/brain/guardrail.py — Compliance guardrail on operator speech."""
import re
from typing import Optional
from shared.types.models import GuardrailAlert

BLOCKED_PHRASES = [
    ("kafolatli foyda",       "yuqori potentsial daromad (xavflar mavjud)"),
    ("guaranteed profit",     "high potential return (risks exist)"),
    ("albatta tasdiqlanadi",  "ariza ko'rib chiqiladi, natija 3-5 kun ichida"),
    ("100% tasdiqlangan",     "ko'rib chiqish jarayoni bor"),
    ("eng yaxshi",            "bizning eng mashhur mahsulotlarimizdan biri"),
    ("самый лучший",          "один из наших наиболее популярных продуктов"),
    ("гарантированный доход", "высокий потенциальный доход (с учётом рисков)"),
    ("точно одобрят",         "заявка будет рассмотрена в течение 3-5 дней"),
]

# compile once
_COMPILED = [(re.compile(re.escape(phrase), re.I), replacement)
             for phrase, replacement in BLOCKED_PHRASES]

class GuardrailChecker:
    def check(self, call_id: str, turn_id: str, text: str) -> Optional[GuardrailAlert]:
        for pattern, replacement in _COMPILED:
            if pattern.search(text):
                return GuardrailAlert(
                    call_id=call_id, turn_id=turn_id,
                    blocked=pattern.pattern,
                    replacement=replacement,
                )
        return None

    def check_kyc(self, kyc_state, text: str) -> None:
        """Advance KYC based on text keywords — convenience wrapper."""
        from kyc import KycStateMachine
        KycStateMachine().advance(kyc_state, text, "operator")
