"""
shared/types/models.py
Canonical data contracts shared by all services.
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


# ─── ASR ──────────────────────────────────────────────────────────────────────

class TranscriptWord(BaseModel):
    ts_start: float          # seconds from call start
    ts_end:   float
    speaker:  Literal["operator", "customer"]
    text:     str
    lang:     Literal["uz", "ru", "mixed"]
    confidence: float = Field(ge=0.0, le=1.0)


class TranscriptChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id:  str
    words:    list[TranscriptWord]
    received_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Brain ────────────────────────────────────────────────────────────────────

class TurnContext(BaseModel):
    turn_id:   str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id:   str
    speaker:   Literal["customer", "operator"]
    intent:    str                    # e.g. "inquiry_credit_card"
    entities:  dict = Field(default_factory=dict)
    sentiment: float = Field(ge=-1.0, le=1.0)
    objections: list[str] = Field(default_factory=list)
    momentum:  float = Field(ge=0.0, le=1.0)
    persona:   Literal["formal", "casual", "analytical", "emotional"] = "casual"
    stress_detected: bool = False


class ActionCard(BaseModel):
    card_id:    str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id:    str
    headline:   str                   # ≤6 words
    body:       str                   # ≤2 sentences
    product:    str
    persona:    Literal["formal", "casual", "analytical", "emotional"]
    confidence: float = Field(ge=0.0, le=1.0)
    card_type:  Literal["nbo", "objection_rebuttal", "kyc_alert", "guardrail"] = "nbo"


KYC_ITEMS = [
    "identity_confirmed", "purpose_of_funds", "source_of_income",
    "pep_screening", "aml_acknowledgment", "product_terms_explained",
    "consent_recorded", "next_steps_communicated",
]

class KycState(BaseModel):
    call_id:  str
    items:    dict[str, Literal["PENDING", "DETECTED", "CONFIRMED"]] = Field(
        default_factory=lambda: {k: "PENDING" for k in KYC_ITEMS}
    )

    @property
    def completeness_pct(self) -> float:
        done = sum(1 for v in self.items.values() if v == "CONFIRMED")
        return round(done / len(self.items) * 100, 1)


class GuardrailAlert(BaseModel):
    call_id:     str
    turn_id:     str
    blocked:     str
    replacement: str
    timestamp:   datetime = Field(default_factory=datetime.utcnow)


# ─── CRM Profile ──────────────────────────────────────────────────────────────

class CustomerProfile(BaseModel):
    customer_id:                str
    age:                        int
    income_bracket:             Literal["low", "mid", "high"]
    owned_products:             list[str] = Field(default_factory=list)
    transaction_volume_monthly: float = 0.0
    previous_rejections:        list[str] = Field(default_factory=list)
    risk_tier:                  Literal["standard", "premium", "vip"] = "standard"
    fetched_at:                 datetime = Field(default_factory=datetime.utcnow)


# ─── Post-Call ────────────────────────────────────────────────────────────────

class CallSummary(BaseModel):
    call_id:           str
    operator_name:     str
    customer_anon_id:  str
    duration_seconds:  int
    branch_name:       str
    detected_needs:    list[str]
    offer_name:        Optional[str]
    offer_details:     Optional[str]
    persona:           str
    outcome:           Literal["accepted", "interested", "rejected", "escalated"]
    next_step:         str
    kyc_done:          int
    kyc_total:         int = 8
    kyc_missing_items: list[str]
    guardrail_count:   int
    quality_score:     float
    summary_text:      str
    created_at:        datetime = Field(default_factory=datetime.utcnow)
