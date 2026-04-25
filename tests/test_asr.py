"""tests/test_asr.py — ASR language detection + WER helper tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest
from services.asr.main import classify_lang

# ── Language classifier ───────────────────────────────────────────────────────

def test_classify_uz_latin():
    lang = classify_lang("Salom, kredit karta haqida so'ramoqchi edim")
    assert lang == "uz"

def test_classify_ru_cyrillic():
    lang = classify_lang("Здравствуйте, я хочу узнать о кредитной карте")
    assert lang == "ru"

def test_classify_mixed():
    lang = classify_lang("Salom пожалуйста kredit")
    assert lang in ("uz", "ru", "mixed")

def test_classify_empty_string():
    lang = classify_lang("")
    assert isinstance(lang, str)

def test_classify_only_digits():
    lang = classify_lang("12345 67890")
    assert isinstance(lang, str)

# ── WER helper (pure Python, no model needed) ─────────────────────────────────

def wer(reference: str, hypothesis: str) -> float:
    """Edit-distance WER."""
    ref = reference.lower().split()
    hyp = hypothesis.lower().split()
    if not ref:
        return 0.0
    d = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1): d[i][0] = i
    for j in range(len(hyp) + 1): d[0][j] = j
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            cost = 0 if ref[i-1] == hyp[j-1] else 1
            d[i][j] = min(d[i-1][j] + 1, d[i][j-1] + 1, d[i-1][j-1] + cost)
    return d[len(ref)][len(hyp)] / len(ref)

def test_wer_perfect_match():
    assert wer("salom dunyo", "salom dunyo") == 0.0

def test_wer_one_substitution():
    score = wer("salom dunyo bor", "salom dunyo yo'q")
    assert abs(score - 1/3) < 0.01

def test_wer_below_30pct_clean_uz():
    ref = "kredit karta olish uchun nima kerak"
    hyp = "kredit karta olish uchun nima kerak"
    assert wer(ref, hyp) < 0.30, "WER target <30% must hold for perfect transcript"

def test_wer_code_switched_sentence():
    ref = "kredit karta хочу получить"
    hyp = "kredit karta хочу получить"
    assert wer(ref, hyp) == 0.0

def test_wer_empty_reference():
    assert wer("", "anything") == 0.0

def test_wer_insertion_penalty():
    score = wer("hello", "hello world extra words")
    # Insertions count → WER > 0
    assert score > 0
