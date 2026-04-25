# CLAUDE.md — BankCopilot Harness
> SQB Bank · Problem 12 · Uzbek/Russian Real-Time AI Sales Assistant

---

## BEHAVIORAL RULES (Karpathy)

### 1. Think Before Coding
Surface ALL assumptions as a bullet list before touching any file.
Ambiguous intent → list interpretations → ask. Never pick silently.

### 2. Simplicity First
Smallest working version. 80 lines beats 800.
No abstraction unless used 3+ times. No framework unless it saves 200+ lines.
Module >300 lines → split it. Dead code → delete immediately.

### 3. Surgical Changes
Only touch files the current task requires.
After every task: `git diff --stat` → anything off-scope gets reverted.
No opportunistic reformats, renames, or refactors.

### 4. Goal-Driven Execution
Every task = a verifiable success criterion.
Write the assertion/test FIRST. Make it pass. Ship when green.
Transform imperative instructions into declarative goals with verification loops.

---

## CONFUSION PROTOCOL (gstack)
If blocked: STOP. Create CONFUSION.md:
- What I expected vs what I see
- Two interpretations
- Best guess + confidence %
- The one question that unblocks me

---

## MISSION
BankCopilot — real-time AI assistant whispered to SQB bank operators during live calls.
Uzbek/Russian bilingual. Edge-first privacy. ≤2s NBO latency. KYC enforced.
Five unique features no other team has: code-switching ASR, Momentum Score,
Persona Engine, Operator Stress Detector, anonymized-edge architecture.

---

## SKILL INDEX — load the relevant skill before starting any module

| Task | Load skill |
|---|---|
| ASR pipeline (Whisper, diarization, code-switch) | `.claude/skills/asr.md` |
| Intent, NBO, KYC, guardrail, stress detector | `.claude/skills/brain.md` |
| Operator Copilot UI (Electron + React overlay) | `.claude/skills/ui.md` |
| Post-call summary + Manager Dashboard | `.claude/skills/post-call.md` |
| Security, encryption, anonymization, PBX | `.claude/skills/security.md` |
| Demo script, judge prep, failure mitigations | `.claude/skills/demo.md` |
| Full system architecture reference | `.claude/skills/architecture.md` |

**Rule:** Read the skill file completely before writing a single line of code for that module.

---

## TECH STACK (quick reference — details in architecture.md)

| Layer | Choice |
|---|---|
| ASR runtime | faster-whisper INT8 (openai/whisper-large-v3) |
| Diarization | pyannote/speaker-diarization-3.1 |
| NLU | Claude claude-sonnet-4-20250514 (anonymized input only) |
| UI | Electron + React + Tailwind (dark mode) |
| Backend | FastAPI Python 3.11 (thin routing, zero business logic in routes) |
| Local DB | SQLite per workstation |
| Central DB | PostgreSQL (manager dashboard) |
| Encryption | AES-256 at rest, TLS 1.3 in transit |

---

## SPRINT ORDER

Phase 0 → Foundation (stub pipeline, CI green)
Phase 1 → ASR (load `asr.md` first)
Phase 2 → Brain / Decision Layer (load `brain.md` first)
Phase 3 → UI Overlay (load `ui.md` first)
Phase 4 → Post-Call Agent (load `post-call.md` first)
Phase 5 → Security Hardening (load `security.md` first)
Phase 6 → Demo Dry Run (load `demo.md` first)

---

## FILE STRUCTURE

```
fintech_hack/
├── CLAUDE.md                   ← this file (harness, thin)
├── CONFUSION.md                ← create when blocked
├── .claude/skills/             ← fat skills, load on demand
│   ├── asr.md
│   ├── brain.md
│   ├── ui.md
│   ├── post-call.md
│   ├── security.md
│   ├── demo.md
│   └── architecture.md
├── apps/overlay/               ← Electron + React
├── apps/dashboard/             ← Manager SPA
├── services/asr/               ← faster-whisper + pyannote
├── services/brain/             ← FastAPI decision layer
├── services/post-call/         ← summary + CRM adapter
├── shared/types/               ← TypeScript + Pydantic contracts
├── shared/vocab/               ← uz_banking_terms.json (200 terms)
├── tests/
└── docker-compose.yml
```
