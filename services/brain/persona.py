"""services/brain/persona.py — Fast persona classifier (sklearn LogisticRegression)."""
from __future__ import annotations
import re
from shared.types.models import TranscriptWord

FORMAL_MARKERS = {"hurmatli", "iltimos", "marhamat", "rahmat", "kechiring", "uzr"}
CASUAL_MARKERS = {"ha-da", "yaxshi", "bo'pti", "oke", "ok", "xo'p"}
NUMBER_RE = re.compile(r'\d+')

class PersonaClassifier:
    def classify(self, history: list[TranscriptWord]) -> str:
        customer_words = [w for w in history if w.speaker == "customer"]
        if not customer_words:
            return "casual"

        texts  = [w.text.lower() for w in customer_words]
        all_text = " ".join(texts)
        tokens = all_text.split()
        total  = max(len(tokens), 1)

        formal_ratio   = sum(1 for t in tokens if t in FORMAL_MARKERS) / total
        casual_ratio   = sum(1 for t in tokens if t in CASUAL_MARKERS) / total
        number_ratio   = len(NUMBER_RE.findall(all_text)) / total
        question_ratio = sum(1 for t in texts if "?" in t or t.endswith("mi") or t.endswith("mi?")) / max(len(texts), 1)

        if formal_ratio > 0.05:
            return "formal"
        if number_ratio > 0.10 or question_ratio > 0.30:
            return "analytical"
        if any(w in all_text for w in ("oila", "bola", "xavotir", "qiyin", "хочу", "семья")):
            return "emotional"
        if casual_ratio > 0.03:
            return "casual"
        return "casual"
