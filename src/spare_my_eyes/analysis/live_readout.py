from dataclasses import dataclass

from spare_my_eyes.analysis.blink_detector import BlinkDetector, BlinkKind
from spare_my_eyes.analysis.distance import ScreenDistanceEstimator
from spare_my_eyes.analysis.gaze import WindowGazeDetector
from spare_my_eyes.capture.face_sample import FaceSample


@dataclass(frozen=True, slots=True)
class LiveReading:
    face_present: bool
    eye_openness: float
    head_yaw_degrees: float
    looking_at_window: bool
    distance_cm: float | None
    complete_blinks: int
    incomplete_blinks: int


class LiveReadout:
    """Runs the same analyzers as the coach on every sample so the camera window can show them."""

    def __init__(
        self,
        blinks: BlinkDetector,
        distance: ScreenDistanceEstimator,
        gaze: WindowGazeDetector,
        open_ear_baseline: float,
    ) -> None:
        self._blinks = blinks
        self._distance = distance
        self._gaze = gaze
        self._open_ear_baseline = open_ear_baseline
        self._blink_counts = {BlinkKind.COMPLETE: 0, BlinkKind.INCOMPLETE: 0}

    def observe(self, sample: FaceSample) -> LiveReading:
        self._count_blink(sample)
        distance = self._distance.update(sample)
        return LiveReading(
            face_present=sample.face_present,
            eye_openness=sample.mean_ear / self._open_ear_baseline,
            head_yaw_degrees=sample.head_yaw_degrees,
            looking_at_window=self._gaze.is_looking_at_window(sample),
            distance_cm=None if distance is None else distance.distance_cm,
            complete_blinks=self._blink_counts[BlinkKind.COMPLETE],
            incomplete_blinks=self._blink_counts[BlinkKind.INCOMPLETE],
        )

    def _count_blink(self, sample: FaceSample) -> None:
        blink = self._blinks.update(sample)
        if blink is not None and blink.kind in self._blink_counts:
            self._blink_counts[blink.kind] += 1
