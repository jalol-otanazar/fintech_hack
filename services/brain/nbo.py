"""services/brain/nbo.py — Next-Best-Offer Engine."""
from shared.types.models import TurnContext, ActionCard, CustomerProfile
from typing import Optional
import uuid

# Scripts per product and persona
SCRIPTS: dict[str, dict[str, dict]] = {
    "credit_card": {
        "formal": {"headline": "Premium kredit karta", "body": "12 oyga 0% foiz, 15M so'm limit. Siz uchun maxsus taklif."},
        "casual":  {"headline": "💳 Kredit karta — 0% foiz!", "body": "12 oyga hech qanday foiz yo'q, 15 mln gacha. Qulay!"},
        "analytical": {"headline": "Kredit karta: foiz 0%, limit 15M", "body": "APR 0% (12 oy), keyin 18%. Minimal to'lov 3%."},
        "emotional": {"headline": "Oilangiz uchun ishonchli karta", "body": "Xavfsiz, qulay, 12 oy foizsiz. Ko'p oilalar ishonadi."},
    },
    "deposit": {
        "formal":     {"headline": "Muddatli depozit taklifi", "body": "Yillik 18% foiz, 3–24 oy muddatga. Ishonchli investitsiya."},
        "casual":     {"headline": "Pullaringiz ishlaydi!", "body": "18% yillik foiz — eng yuqori stavka. Hoziroq oching!"},
        "analytical": {"headline": "Depozit: 18% p.a., 3–24 oy", "body": "Har oylik hisoblash. Kapital + foiz — kafolatlangan."},
        "emotional":  {"headline": "Kelajak uchun xavfsiz joy", "body": "Pullaringiz saqlanadi va o'sadi. Oilangiz xotirjam bo'ladi."},
    },
    "student_card": {
        "formal":     {"headline": "Talaba kartasi xizmati", "body": "Yosh mijozlar uchun imtiyozli shart. Ariza 10 daqiqada."},
        "casual":     {"headline": "🎓 Talaba karta — tekin!", "body": "Yillik xizmat haqsiz, cashback 2%. Ilova orqali boshqar."},
        "analytical": {"headline": "Student card: 0 yillik haq", "body": "Cashback 2%, overdraft 500k so'm. 18–25 yosh uchun."},
        "emotional":  {"headline": "O'qish davri uchun ishonchli karta", "body": "Ota-onangiz xotirjam — karta xavfsiz va nazorat ostida."},
    },
    "premium_deposit": {
        "formal":     {"headline": "VIP depozit dasturi", "body": "Maxsus shartlar: 21% yillik, 6–36 oy. Faqat yuqori daromadli mijozlar uchun."},
        "casual":     {"headline": "💎 Premium depozit — 21%!", "body": "Siz uchun maxsus: 21% yillik. Chegaralangan taklif!"},
        "analytical": {"headline": "Premium depozit: 21% p.a., 6–36 oy", "body": "APY 21%. Oylik hisoblash. Minimum 50M so'm."},
        "emotional":  {"headline": "Oilangiz kelajagi uchun eng yaxshi", "body": "21% foiz — pullaringiz tezroq o'sadi. Ishonchli va xavfsiz."},
    },
    "premium_card": {
        "formal":     {"headline": "Platinum kredit karta", "body": "50M limit, lounge kirish, 0% foiz 24 oy. Maxsus VIP mijozlar uchun."},
        "casual":     {"headline": "💳 Platinum karta — bepul lounge!", "body": "50 mln limit, airport lounge, cashback 3%. Faqat siz uchun!"},
        "analytical": {"headline": "Platinum: limit 50M, cashback 3%", "body": "APR 0% (24 oy), keyin 16%. Lounge kirish, travel insurance."},
        "emotional":  {"headline": "Siz maxsus davolanishga loyiqsiz", "body": "Platinum imtiyozlar — lounge, sug'urta, cashback. Hayotingizni osonlashtiradi."},
    },
}

PRIORITY_MATRIX = [
    # (condition_fn, product)
    (lambda ctx: ctx.intent == "inquiry_credit_card", "credit_card"),
    (lambda ctx: ctx.intent == "inquiry_deposit",     "deposit"),
    (lambda ctx: ctx.intent == "inquiry_loan",        "credit_card"),
    (lambda ctx: ctx.entities.get("age_young"),       "student_card"),
    (lambda ctx: True,                                "credit_card"),  # fallback
]

_INCOME_UPGRADE: dict[str, dict[str, str]] = {
    "high": {"credit_card": "premium_card", "deposit": "premium_deposit"},
    "mid":  {},
    "low":  {},
}


class NBOEngine:
    def decide(self, ctx: TurnContext, profile: CustomerProfile | None = None) -> Optional[ActionCard]:
        if ctx.entities.get("pep_flag"):
            return None

        product = self._select_product(ctx, profile)
        if not product or product not in SCRIPTS:
            return None

        script = SCRIPTS[product].get(ctx.persona, SCRIPTS[product]["casual"])
        confidence = self._calculate_confidence(ctx, profile, product)

        return ActionCard(
            call_id=ctx.call_id,
            headline=script["headline"],
            body=script["body"],
            product=product,
            persona=ctx.persona,
            confidence=confidence,
            card_type="nbo",
        )

    def _select_product(self, ctx: TurnContext, profile: CustomerProfile | None) -> str | None:
        candidates = [prod for cond, prod in PRIORITY_MATRIX if cond(ctx)]
        if not candidates:
            return None
        if profile is None:
            return candidates[0]
        upgrades = _INCOME_UPGRADE.get(profile.income_bracket, {})
        upgraded = [upgrades.get(p, p) for p in candidates]
        # First pass: upgraded candidates not already owned
        for prod in upgraded:
            if prod not in profile.owned_products:
                return prod
        # Second pass: original candidates (customer owns premium, offer standard)
        for prod in candidates:
            if prod not in profile.owned_products:
                return prod
        return None  # customer owns every candidate

    def _calculate_confidence(
        self, ctx: TurnContext, profile: CustomerProfile | None, product: str
    ) -> float:
        base = 0.60 + ctx.momentum * 0.35
        if profile is not None:
            if profile.risk_tier == "vip":
                base += 0.05
            if profile.income_bracket == "high":
                base += 0.03
            base -= profile.previous_rejections.count(product) * 0.10
        return round(max(0.30, min(0.95, base)), 2)
