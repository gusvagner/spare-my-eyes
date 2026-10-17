import logging
from collections.abc import Callable
from dataclasses import replace

from spare_my_eyes.calibration import CalibrationResult, CalibrationSession
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.coach import Coach
from spare_my_eyes.coaching.notifier import Notifier, TrayStatus
from spare_my_eyes.settings import Settings
from spare_my_eyes.settings_store import SettingsStore
from spare_my_eyes.structured_log import log_event


class EyeCareController:
    """Runs calibration until the user is calibrated, then hands samples to the Coach."""

    def __init__(
        self,
        settings: Settings,
        store: SettingsStore,
        coach_factory: Callable[[Settings], Coach],
        notifier: Notifier,
        clock: Clock,
        logger: logging.Logger,
    ) -> None:
        self._settings = settings
        self._store = store
        self._coach_factory = coach_factory
        self._notifier = notifier
        self._clock = clock
        self._logger = logger
        self._coach = coach_factory(settings)
        self._calibration: CalibrationSession | None = None
        if not settings.is_calibrated:
            self.recalibrate()

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def is_paused(self) -> bool:
        return self._coach.is_paused

    @property
    def is_calibrating(self) -> bool:
        return self._calibration is not None

    def recalibrate(self) -> None:
        self._coach.suspend()
        now = self._clock.now()
        self._calibration = CalibrationSession(now)
        self._notifier.set_status(TrayStatus.CALIBRATING, None)
        self._notifier.show_calibration(self._calibration.progress(now))

    def on_sample(self, sample: FaceSample) -> None:
        if self._calibration is None:
            self._coach.on_sample(sample)
            return
        progress = self._calibration.update(sample)
        result = self._calibration.result
        if result is None:
            self._notifier.show_calibration(progress)
            return
        self._finish_calibration(result)

    def tick(self) -> None:
        if self._calibration is None:
            self._coach.tick()

    def on_camera_status(self, status: CameraStatus) -> None:
        self._coach.on_camera_status(status)
        if status is not CameraStatus.ACTIVE:
            self._cancel_calibration()
            return
        if not self._settings.is_calibrated and self._calibration is None:
            self.recalibrate()

    def pause_for(self, seconds: float) -> None:
        self._cancel_calibration()
        self._coach.pause_for(seconds)

    def start_break_now(self) -> None:
        if self._calibration is None:
            self._coach.start_break_now()

    def snooze_break(self) -> None:
        self._coach.snooze_break()

    def skip_break(self) -> None:
        self._coach.skip_break()

    def _cancel_calibration(self) -> None:
        if self._calibration is None:
            return
        self._calibration = None
        self._notifier.hide_calibration()

    def _finish_calibration(self, result: CalibrationResult) -> None:
        self._settings = replace(
            self._settings,
            open_ear_baseline=result.open_ear_baseline,
            focal_scale=result.focal_scale,
        )
        self._store.save(self._settings)
        self._calibration = None
        self._notifier.hide_calibration()
        self._coach = self._coach_factory(self._settings)
        log_event(
            self._logger,
            logging.INFO,
            "calibration_completed",
            open_ear_baseline=result.open_ear_baseline,
            focal_scale=result.focal_scale,
        )
