from collections import deque
from dataclasses import dataclass

from spare_my_eyes.analysis.blink_detector import Blink, BlinkKind
from spare_my_eyes.capture.face_sample import FaceSample

_TOLERANCE_SECONDS = 1e-6


@dataclass(frozen=True, slots=True)
class BlinkStats:
    blinks_per_minute: float
    incomplete_ratio: float
    covered_seconds: float
    window_full: bool


class BlinkRateMonitor:
    MAX_SAMPLE_GAP_SECONDS = 1.0

    def __init__(self, window_seconds: float = 120.0) -> None:
        self._window = window_seconds
        self._presence_seconds = 0.0
        self._last_present_at: float | None = None
        self._blinks: deque[tuple[float, BlinkKind]] = deque()

    def observe(self, sample: FaceSample) -> None:
        if not sample.face_present:
            self._last_present_at = None
            return
        if self._last_present_at is not None:
            gap = sample.timestamp - self._last_present_at
            self._presence_seconds += min(max(gap, 0.0), self.MAX_SAMPLE_GAP_SECONDS)
        self._last_present_at = sample.timestamp
        self._drop_expired()

    def record(self, blink: Blink) -> None:
        if blink.is_spontaneous:
            self._blinks.append((self._presence_seconds, blink.kind))

    def stats(self) -> BlinkStats | None:
        covered = min(self._presence_seconds, self._window)
        if covered <= 0:
            return None
        count = len(self._blinks)
        incomplete = sum(1 for _, kind in self._blinks if kind is BlinkKind.INCOMPLETE)
        return BlinkStats(
            blinks_per_minute=count * 60.0 / covered,
            incomplete_ratio=incomplete / count if count else 0.0,
            covered_seconds=covered,
            window_full=covered >= self._window - _TOLERANCE_SECONDS,
        )

    def reset(self) -> None:
        self._presence_seconds = 0.0
        self._last_present_at = None
        self._blinks.clear()

    def _drop_expired(self) -> None:
        oldest_allowed = self._presence_seconds - self._window
        while self._blinks and self._blinks[0][0] < oldest_allowed:
            self._blinks.popleft()
