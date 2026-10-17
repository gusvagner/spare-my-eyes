import statistics
from collections import deque
from dataclasses import dataclass

from spare_my_eyes.capture.face_sample import FaceSample

ARM_LENGTH_CM = 60.0


def focal_scale_from_calibration(iris_diameter_px_at_arm_length: float) -> float:
    return iris_diameter_px_at_arm_length * ARM_LENGTH_CM


@dataclass(frozen=True, slots=True)
class DistanceThresholds:
    too_close_cm: float = 50.0
    clear_cm: float = 55.0
    hold_seconds: float = 30.0


@dataclass(frozen=True, slots=True)
class DistanceReading:
    distance_cm: float
    too_close: bool


DEFAULT_DISTANCE_THRESHOLDS = DistanceThresholds()


class ScreenDistanceEstimator:
    SMOOTHING_SAMPLES = 10

    def __init__(
        self, focal_scale: float, thresholds: DistanceThresholds = DEFAULT_DISTANCE_THRESHOLDS
    ) -> None:
        if focal_scale <= 0:
            raise ValueError(f"focal_scale must be > 0, got {focal_scale}")
        self._focal_scale = focal_scale
        self._thresholds = thresholds
        self._recent: deque[float] = deque(maxlen=self.SMOOTHING_SAMPLES)
        self._close_since: float | None = None
        self._too_close = False

    def update(self, sample: FaceSample) -> DistanceReading | None:
        if not sample.face_present or sample.iris_diameter_px <= 0:
            return None
        self._recent.append(sample.iris_diameter_px)
        distance = self._focal_scale / statistics.median(self._recent)
        self._too_close = self._next_too_close(sample.timestamp, distance)
        return DistanceReading(distance_cm=distance, too_close=self._too_close)

    def reset(self) -> None:
        self._recent.clear()
        self._close_since = None
        self._too_close = False

    def _next_too_close(self, timestamp: float, distance: float) -> bool:
        if self._too_close:
            return self._still_too_close(distance)
        if distance >= self._thresholds.too_close_cm:
            self._close_since = None
            return False
        if self._close_since is None:
            self._close_since = timestamp
        return timestamp - self._close_since >= self._thresholds.hold_seconds

    def _still_too_close(self, distance: float) -> bool:
        if distance <= self._thresholds.clear_cm:
            return True
        self._close_since = None
        return False
