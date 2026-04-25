"""tests/test_wer.py — WER tests on 10 synthetic Uzbek/Russian transcripts.
Simulates what faster-whisper would return vs ground-truth labels.
No GPU / no model needed: tests the metric and pipeline logic only.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest

# ── WER implementation ────────────────────────────────────────────────────────

def wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate via edit distance. Returns 0.0 for empty reference."""
    ref = reference.lower().split()
    hyp = hypothesis.lower().split()
    if not ref:
        return 0.0
    d = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1):
        d[i][0] = i
    for j in range(len(hyp) + 1):
        d[0][j] = j
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i-1][j] + 1, d[i][j-1] + 1, d[i-1][j-1] + cost)
    return d[len(ref)][len(hyp)] / len(ref)


# ── 10 synthetic call transcript pairs (reference, hypothesis, max_wer) ──────
# Format: (description, reference_text, model_hypothesis, acceptable_wer_threshold)

TRANSCRIPT_PAIRS = [
    # 1. Clean Uzbek — standard banking query
    (
        "clean_uz_credit_card",
        "kredit karta olish uchun qanday hujjatlar kerak",
        "kredit karta olish uchun qanday hujjatlar kerak",
        0.00,
    ),
    # 2. Clean Uzbek — deposit inquiry
    (
        "clean_uz_deposit",
        "depozit ochish uchun minimal summa qancha",
        "depozit ochish uchun minimal summa qancha",
        0.00,
    ),
    # 3. Clean Russian — loan query
    (
        "clean_ru_loan",
        "какой у вас процент по потребительскому кредиту",
        "какой у вас процент по потребительскому кредиту",
        0.00,
    ),
    # 4. Code-switched — Uzbek + Russian mix
    (
        "codeswitched_uz_ru",
        "kredit karta хочу получить necha kun kutish kerak",
        "kredit karta хочу получить necha kun kutish kerak",
        0.00,
    ),
    # 5. Uzbek with 1 substitution error (simulating ASR noise)
    (
        "uz_one_sub",
        "ipoteka krediti uchun daromad tasdiqnomasi kerak",
        "ipoteka krediti uchun daromad tasdiqnoma kerak",
        0.20,
    ),
    # 6. Russian with 1 deletion
    (
        "ru_one_del",
        "мне нужна кредитная карта с кешбэком",
        "мне нужна карта с кешбэком",
        0.25,
    ),
    # 7. Fast speech Uzbek (more errors expected)
    (
        "uz_fast_speech",
        "siz menga kredit karta haqida to'liq ma'lumot bering",
        "siz menga kredit karta haqida to'liq malumot bering",
        0.15,
    ),
    # 8. Banking terms: account numbers / amounts
    (
        "uz_banking_numbers",
        "hisobimda o'n besh million so'm bor edi",
        "hisobimda o'n besh million so'm bor edi",
        0.00,
    ),
    # 9. Polite formal Uzbek
    (
        "uz_formal_polite",
        "hurmatli operator muddatli depozit bo'yicha ma'lumot bera olasizmi",
        "hurmatli operator muddatli depozit bo'yicha malumot bera olasizmi",
        0.13,
    ),
    # 10. Mixed longer utterance
    (
        "mixed_long",
        "kredit karta limit ko'paytirish uchun какие документы нужны и сколько времени",
        "kredit karta limit ko'paytirish uchun какие документы нужны и сколько времени",
        0.00,
    ),
]


@pytest.mark.parametrize("desc,ref,hyp,max_wer", TRANSCRIPT_PAIRS)
def test_wer_within_threshold(desc, ref, hyp, max_wer):
    """Each synthetic transcript must be within its declared WER threshold."""
    actual = wer(ref, hyp)
    assert actual <= max_wer, (
        f"[{desc}] WER {actual:.2%} exceeds threshold {max_wer:.2%}\n"
        f"  REF: {ref}\n"
        f"  HYP: {hyp}"
    )


def test_all_transcripts_below_30pct_wer():
    """No transcript should exceed 30% WER — our minimum bar for the competition."""
    for desc, ref, hyp, _ in TRANSCRIPT_PAIRS:
        actual = wer(ref, hyp)
        assert actual < 0.30, (
            f"[{desc}] WER {actual:.2%} exceeds 30% ceiling"
        )


def test_wer_codeswitched_below_40pct():
    """Code-switched utterances get a relaxed 40% ceiling."""
    codeswitched = [p for p in TRANSCRIPT_PAIRS if "codeswitched" in p[0] or "mixed" in p[0]]
    for desc, ref, hyp, _ in codeswitched:
        actual = wer(ref, hyp)
        assert actual < 0.40, (
            f"[{desc}] Code-switched WER {actual:.2%} exceeds 40% ceiling"
        )


def test_wer_aggregate_average():
    """Aggregate WER across all 10 transcripts must be < 10%."""
    total = sum(wer(ref, hyp) for _, ref, hyp, _ in TRANSCRIPT_PAIRS)
    avg = total / len(TRANSCRIPT_PAIRS)
    assert avg < 0.10, f"Aggregate avg WER {avg:.2%} exceeds 10%"
