from dataclasses import dataclass
from enum import StrEnum

from spare_my_eyes.capture.face_sample import FaceSample


class BlinkKind(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    DELIBERATE = "deliberate"


@dataclass(frozen=True, slots=True)
class Blink:
    ended_at: float
    duration_seconds: float
    min_ear_ratio: float
    kind: BlinkKind

    @property
    def is_spontaneous(self) -> bool:
        return self.kind is not BlinkKind.DELIBERATE


@dataclass(frozen=True, slots=True)
class BlinkThresholds:
    closing_ratio: float = 0.8
    complete_ratio: float = 0.4
    max_spontaneous_seconds: float = 0.5


DEFAULT_BLINK_THRESHOLDS = BlinkThresholds()


class BlinkDetector:
    def __init__(
        self, open_ear_baseline: float, thresholds: BlinkThresholds = DEFAULT_BLINK_THRESHOLDS
    ) -> None:
        if open_ear_baseline <= 0:
            raise ValueError(f"open_ear_baseline must be > 0, got {open_ear_baseline}")
        self._baseline = open_ear_baseline
        self._thresholds = thresholds
        self._closed_since: float | None = None
        self._min_ratio = 1.0

    def update(self, sample: FaceSample) -> Blink | None:
        if not sample.face_present:
            self.reset()
            return None
        ratio = sample.mean_ear / self._baseline
        if ratio < self._thresholds.closing_ratio:
            self._track_closure(sample.timestamp, ratio)
            return None
        return self._finish_closure(sample.timestamp)

    def reset(self) -> None:
        self._closed_since = None

    def _track_closure(self, timestamp: float, ratio: float) -> None:
        if self._closed_since is None:
            self._closed_since = timestamp
            self._min_ratio = ratio
            return
        self._min_ratio = min(self._min_ratio, ratio)

    def _finish_closure(self, timestamp: float) -> Blink | None:
        if self._closed_since is None:
            return None
        duration = timestamp - self._closed_since
        self._closed_since = None
        return Blink(timestamp, duration, self._min_ratio, self._classify(duration))

    def _classify(self, duration: float) -> BlinkKind:
        if duration > self._thresholds.max_spontaneous_seconds:
            return BlinkKind.DELIBERATE
        if self._min_ratio < self._thresholds.complete_ratio:
            return BlinkKind.COMPLETE
        return BlinkKind.INCOMPLETE
