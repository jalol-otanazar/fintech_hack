-- services/post-call/schema.sql
-- PostgreSQL schema for BankCopilot

CREATE TABLE IF NOT EXISTS operators (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    branch_name   VARCHAR(120) NOT NULL,
    language_pref VARCHAR(4) DEFAULT 'uz',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS calls (
    id                 VARCHAR(64) PRIMARY KEY,
    operator_id        INTEGER REFERENCES operators(id),
    customer_anon_id   VARCHAR(64) NOT NULL,
    branch_name        VARCHAR(120),
    started_at         TIMESTAMPTZ NOT NULL,
    ended_at           TIMESTAMPTZ,
    duration_seconds   INTEGER,
    outcome            VARCHAR(20) CHECK (outcome IN ('accepted','interested','rejected','escalated')),
    offer_name         VARCHAR(120),
    persona            VARCHAR(20),
    quality_score      NUMERIC(5,2),
    kyc_done           SMALLINT DEFAULT 0,
    kyc_total          SMALLINT DEFAULT 8,
    guardrail_count    SMALLINT DEFAULT 0,
    summary_text       TEXT,
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kyc_items (
    id       SERIAL PRIMARY KEY,
    call_id  VARCHAR(64) REFERENCES calls(id) ON DELETE CASCADE,
    item     VARCHAR(60) NOT NULL,
    status   VARCHAR(12) DEFAULT 'PENDING'
);

CREATE TABLE IF NOT EXISTS guardrail_events (
    id           SERIAL PRIMARY KEY,
    call_id      VARCHAR(64) REFERENCES calls(id) ON DELETE CASCADE,
    turn_id      VARCHAR(64),
    blocked      TEXT NOT NULL,
    replacement  TEXT NOT NULL,
    fired_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quality_scores (
    id              SERIAL PRIMARY KEY,
    call_id         VARCHAR(64) REFERENCES calls(id) ON DELETE CASCADE,
    kyc_component   NUMERIC(5,2),
    offer_component NUMERIC(5,2),
    guardrail_component NUMERIC(5,2),
    efficiency_component NUMERIC(5,2),
    total           NUMERIC(5,2),
    calculated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for dashboard queries
CREATE INDEX IF NOT EXISTS idx_calls_operator  ON calls(operator_id);
CREATE INDEX IF NOT EXISTS idx_calls_branch    ON calls(branch_name);
CREATE INDEX IF NOT EXISTS idx_calls_created   ON calls(created_at);
CREATE INDEX IF NOT EXISTS idx_calls_quality   ON calls(quality_score);
CREATE INDEX IF NOT EXISTS idx_guardrail_call  ON guardrail_events(call_id);
