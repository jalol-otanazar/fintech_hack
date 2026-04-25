"""services/brain/stress.py — Operator Stress Detector."""
import time
from collections import deque
from shared.types.models import TranscriptWord


class StressDetector:
    def __init__(self):
        self._baseline_wpm: float | None = None
        self._baseline_window: list[float] = []   # word durations in first 60s
        self._call_start: float = time.time()
        self._recent_phrases: deque[str] = deque(maxlen=20)
        self._last_word_end: float = 0.0
        self._long_pauses: int = 0

    def _words_per_minute(self, words: list[TranscriptWord]) -> float:
        if len(words) < 2:
            return 0.0
        duration = words[-1].ts_end - words[0].ts_start
        return len(words) / max(duration / 60, 0.001)

    def _set_baseline(self, words: list[TranscriptWord]):
        """Build baseline from first 60 seconds of operator speech."""
        if self._baseline_wpm is not None:
            return
        op_words = [w for w in words if w.speaker == "operator"]
        if op_words and op_words[-1].ts_end > 60:
            wpm = self._words_per_minute(op_words)
            if wpm > 0:
                self._baseline_wpm = wpm

    def check(self, words: list[TranscriptWord]) -> bool:
        """Return True if operator stress detected (2+ signals)."""
        op_words = [w for w in words if w.speaker == "operator"]
        if not op_words:
            return False

        self._set_baseline(op_words)
        signals = 0

        # Signal 1: speech rate > 20% above baseline
        if self._baseline_wpm:
            current_wpm = self._words_per_minute(op_words)
            if current_wpm > self._baseline_wpm * 1.20:
                signals += 1

        # Signal 2: pause > 3s before answer
        if op_words and self._last_word_end > 0:
            pause = op_words[0].ts_start - self._last_word_end
            if pause > 3.0:
                signals += 1
        if op_words:
            self._last_word_end = op_words[-1].ts_end

        # Signal 3: same phrase repeated twice in last 30s window
        phrase = " ".join(w.text.lower() for w in op_words[-3:])
        if phrase in self._recent_phrases:
            signals += 1
        self._recent_phrases.append(phrase)

        return signals >= 2
