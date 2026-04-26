"""services/brain/momentum.py — Rolling Momentum Score."""
from collections import deque

class MomentumCalculator:
    def __init__(self):
        self._sentiments: deque[float] = deque(maxlen=5)
        self._questions = 0
        self._total_turns = 0
        self._entities_seen: set = set()
        self._call_start = __import__("time").time()

    def update(self, sentiment: float, entities: dict | None = None,
               is_question: bool = False, expected_duration: float = 300.0) -> float:
        self._sentiments.append(sentiment)
        self._total_turns += 1
        if is_question:
            self._questions += 1
        if entities:
            self._entities_seen.update(entities.keys())

        sentiment_trend  = self._sentiment_trend()
        question_engage  = min(self._questions / max(self._total_turns, 1), 1.0)
        topic_depth      = min(len(self._entities_seen) / 5.0, 1.0)
        call_time_factor = self._time_factor(expected_duration)

        momentum = (
            sentiment_trend  * 0.35 +
            question_engage  * 0.25 +
            topic_depth      * 0.20 +
            call_time_factor * 0.20
        )
        return round(max(0.0, min(1.0, momentum)), 3)

    def _sentiment_trend(self) -> float:
        if not self._sentiments:
            return 0.5
        # Use mean sentiment (not slope) — a consistently positive call should score high
        avg = sum(self._sentiments) / len(self._sentiments)
        # Map from [-1.0, 1.0] → [0.0, 1.0]
        return max(0.0, min(1.0, (avg + 1.0) / 2.0))

    def _time_factor(self, expected: float) -> float:
        elapsed = __import__("time").time() - self._call_start
        ratio = elapsed / expected
        # Peaks at 0.4–0.7 of expected duration
        if ratio < 0.4:
            return ratio / 0.4
        elif ratio <= 0.7:
            return 1.0
        else:
            return max(0.0, 1.0 - (ratio - 0.7) / 0.3)
