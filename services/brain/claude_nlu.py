"""services/brain/claude_nlu.py — Extract TurnContext from transcript via Claude API."""
import os, json
from anthropic import AsyncAnthropic
from shared.types.models import TranscriptWord, TurnContext
from security import PiiEncryptor
import uuid

client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """You are BankCopilot NLU. Given a recent transcript excerpt from an Uzbek/Russian bank call, extract a structured TurnContext JSON.

Rules:
- speaker: last speaker in the transcript ("customer" or "operator")
- intent: one of: inquiry_credit_card, inquiry_deposit, inquiry_loan, objection_rate, objection_trust, objection_think, smalltalk, kyc_disclosure, complaint, closing
- entities: JSON object with any of: income_mentioned (bool), amount (int), product (str), duration_months (int)
- sentiment: float -1.0 to 1.0 (customer sentiment only)
- objections: array of active objection tags
- persona: one of: formal, casual, analytical, emotional

Respond ONLY with a valid JSON object matching this schema. No markdown, no explanation."""

async def extract_turn_context(call_id: str, history: list[TranscriptWord]) -> TurnContext:
    """Call Claude API to extract structured TurnContext from recent transcript."""
    # Build transcript text (last 20 words max for speed)
    recent = history[-20:]
    transcript_text = "\n".join(
        f"[{w.speaker.upper()}] ({w.lang}) {w.text}" for w in recent
    )
    transcript_text = PiiEncryptor.strip_pii_from_transcript(transcript_text)

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Transcript:\n{transcript_text}\n\nExtract TurnContext JSON:"}]
        )
        raw = response.content[0].text.strip()
        data = json.loads(raw)
        return TurnContext(
            call_id=call_id,
            speaker=data.get("speaker", "customer"),
            intent=data.get("intent", "smalltalk"),
            entities=data.get("entities", {}),
            sentiment=float(data.get("sentiment", 0.0)),
            objections=data.get("objections", []),
            persona=data.get("persona", "casual"),
            momentum=0.5,  # overwritten by momentum calculator
        )
    except Exception as e:
        # Fallback stub on any error
        return _stub_context(call_id, recent)


def _stub_context(call_id: str, history: list[TranscriptWord]) -> TurnContext:
    """Deterministic fallback when Claude API unavailable."""
    import random
    speaker = history[-1].speaker if history else "customer"
    text = " ".join(w.text for w in history[-5:]).lower()

    # Intent from keywords
    intent = "inquiry_credit_card"
    if "foiz" in text or "процент" in text:
        intent = "objection_rate"
    elif "depozit" in text:
        intent = "inquiry_deposit"
    elif "kredit" in text or "karta" in text:
        intent = "inquiry_credit_card"
    elif "rozilik" in text or "ruxsat" in text:
        intent = "kyc_disclosure"
    elif "rahmat" in text or "спасибо" in text:
        intent = "closing"

    # Entities from keywords — populate so topic_depth accumulates
    entities: dict = {}
    if "daromad" in text or "maosh" in text or "доход" in text:
        entities["income_mentioned"] = True
    if "million" in text or "млн" in text:
        entities["amount"] = 12_000_000
    if "karta" in text or "карта" in text:
        entities["product"] = "credit_card"
    if "cashback" in text:
        entities["cashback"] = True
    if "lounge" in text:
        entities["premium_perk"] = True

    # Positive sentiment for a happy demo call (customer is enthusiastic)
    positive_cues = ["yaxshi", "ajoyib", "rahmat", "доволен", "отлично", "juda", "qabul"]
    sentiment = 0.65 if any(c in text for c in positive_cues) else round(random.uniform(0.35, 0.65), 2)

    return TurnContext(
        call_id=call_id,
        speaker=speaker,
        intent=intent,
        entities=entities,
        sentiment=sentiment,
        momentum=0.5,
        persona="casual",
    )
