from spare_my_eyes.analysis.distance import DistanceReading, ScreenDistanceEstimator
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.coaching.cooldown import Cooldown
from spare_my_eyes.coaching.notifier import Notifier

MOVE_BACK_MESSAGE = "Move back a little"


class DistanceAlertPolicy:
    def __init__(
        self, estimator: ScreenDistanceEstimator, cooldown: Cooldown, notifier: Notifier
    ) -> None:
        self._estimator = estimator
        self._cooldown = cooldown
        self._notifier = notifier
        self._visible = False

    def on_sample(self, sample: FaceSample) -> None:
        reading = self._estimator.update(sample)
        if reading is None:
            return
        if self._visible:
            self._hide_when_clear(reading, sample.timestamp)
            return
        if reading.too_close and self._cooldown.is_ready(sample.timestamp):
            self._notifier.show_distance_alert(MOVE_BACK_MESSAGE)
            self._visible = True

    def on_tick(self, now: float) -> None:
        return None

    def suspend(self) -> None:
        if self._visible:
            self._notifier.hide_distance_alert()
        self._visible = False
        self._estimator.reset()

    def _hide_when_clear(self, reading: DistanceReading, now: float) -> None:
        if reading.too_close:
            return
        self._notifier.hide_distance_alert()
        self._visible = False
        self._cooldown.start(now)
