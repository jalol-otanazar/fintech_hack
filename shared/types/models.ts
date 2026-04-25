// shared/types/models.ts  — TypeScript mirror of Pydantic contracts

export type Lang = "uz" | "ru" | "mixed";
export type Speaker = "operator" | "customer";
export type Persona = "formal" | "casual" | "analytical" | "emotional";
export type KycStatus = "PENDING" | "DETECTED" | "CONFIRMED";
export type CardType = "nbo" | "objection_rebuttal" | "kyc_alert" | "guardrail";
export type Outcome = "accepted" | "interested" | "rejected" | "escalated";

export interface TranscriptWord {
  ts_start: number;
  ts_end: number;
  speaker: Speaker;
  text: string;
  lang: Lang;
  confidence: number;
}

export const KYC_ITEMS = [
  "identity_confirmed", "purpose_of_funds", "source_of_income",
  "pep_screening", "aml_acknowledgment", "product_terms_explained",
  "consent_recorded", "next_steps_communicated",
] as const;
export type KycItem = typeof KYC_ITEMS[number];

export interface TurnContext {
  turn_id: string;
  call_id: string;
  speaker: Speaker;
  intent: string;
  entities: Record<string, unknown>;
  sentiment: number;
  objections: string[];
  momentum: number;
  persona: Persona;
  stress_detected: boolean;
  nbo?: ActionCard;
  kyc?: Record<KycItem, KycStatus>;
  guardrail?: GuardrailAlert;
}

export interface ActionCard {
  card_id: string;
  call_id: string;
  headline: string;
  body: string;
  product: string;
  persona: Persona;
  confidence: number;
  card_type: CardType;
}

export interface GuardrailAlert {
  call_id: string;
  turn_id: string;
  blocked: string;
  replacement: string;
  timestamp: string;
}

// WebSocket message envelope
export type WsMessage =
  | { type: "transcript_chunk"; payload: TranscriptWord[] }
  | { type: "turn_context";     payload: TurnContext }
  | { type: "guardrail_alert";  payload: GuardrailAlert }
  | { type: "operator_stress";  payload: { call_id: string } }
  | { type: "call_end";         payload: { call_id: string } }
  | { type: "heartbeat";        payload: { ts: number } };
