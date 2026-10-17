import statistics
from dataclasses import dataclass
from enum import StrEnum

from spare_my_eyes.analysis.distance import focal_scale_from_calibration
from spare_my_eyes.capture.face_sample import FaceSample


class CalibrationStep(StrEnum):
    LOOK_AT_SCREEN = "look_at_screen"
    ARM_LENGTH = "arm_length"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class CalibrationProgress:
    step: CalibrationStep
    seconds_left: float


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    open_ear_baseline: float
    focal_scale: float


class CalibrationSession:
    STEP_SECONDS = 10.0
    MIN_SAMPLES_PER_STEP = 30

    def __init__(self, started_at: float) -> None:
        self._step = CalibrationStep.LOOK_AT_SCREEN
        self._step_started_at = started_at
        self._values: list[float] = []
        self._open_ear_baseline = 0.0
        self._result: CalibrationResult | None = None

    @property
    def result(self) -> CalibrationResult | None:
        return self._result

    def update(self, sample: FaceSample) -> CalibrationProgress:
        if self._step is CalibrationStep.DONE:
            return self.progress(sample.timestamp)
        if sample.face_present:
            self._values.append(self._measure(sample))
        if sample.timestamp - self._step_started_at >= self.STEP_SECONDS:
            self._finish_step(sample.timestamp)
        return self.progress(sample.timestamp)

    def progress(self, now: float) -> CalibrationProgress:
        if self._step is CalibrationStep.DONE:
            return CalibrationProgress(self._step, 0.0)
        elapsed = now - self._step_started_at
        return CalibrationProgress(self._step, max(0.0, self.STEP_SECONDS - elapsed))

    def _measure(self, sample: FaceSample) -> float:
        if self._step is CalibrationStep.LOOK_AT_SCREEN:
            return sample.mean_ear
        return sample.iris_diameter_px

    def _finish_step(self, now: float) -> None:
        self._step_started_at = now
        values, self._values = self._values, []
        if len(values) < self.MIN_SAMPLES_PER_STEP:
            return
        self._advance(statistics.median(values))

    def _advance(self, median: float) -> None:
        if self._step is CalibrationStep.LOOK_AT_SCREEN:
            self._open_ear_baseline = median
            self._step = CalibrationStep.ARM_LENGTH
            return
        focal_scale = focal_scale_from_calibration(median)
        self._result = CalibrationResult(self._open_ear_baseline, focal_scale)
        self._step = CalibrationStep.DONE
