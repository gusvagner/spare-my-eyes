from dataclasses import dataclass

from spare_my_eyes.calibration import CalibrationProgress
from spare_my_eyes.coaching.break_session import BreakProgress
from spare_my_eyes.coaching.notifier import TrayStatus


@dataclass(frozen=True, slots=True)
class NotifierCall:
    name: str
    argument: object = None


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[NotifierCall] = []
        self.blink_nudge: str | None = None
        self.distance_alert: str | None = None
        self.break_progress: BreakProgress | None = None
        self.calibration: CalibrationProgress | None = None
        self.status: TrayStatus | None = None
        self.blinks_per_minute: float | None = None

    def count(self, name: str) -> int:
        return sum(1 for call in self.calls if call.name == name)

    def show_blink_nudge(self, message: str) -> None:
        self.calls.append(NotifierCall("show_blink_nudge", message))
        self.blink_nudge = message

    def hide_blink_nudge(self) -> None:
        self.calls.append(NotifierCall("hide_blink_nudge"))
        self.blink_nudge = None

    def show_distance_alert(self, message: str) -> None:
        self.calls.append(NotifierCall("show_distance_alert", message))
        self.distance_alert = message

    def hide_distance_alert(self) -> None:
        self.calls.append(NotifierCall("hide_distance_alert"))
        self.distance_alert = None

    def show_break(self, progress: BreakProgress) -> None:
        self.calls.append(NotifierCall("show_break", progress))
        self.break_progress = progress

    def hide_break(self) -> None:
        self.calls.append(NotifierCall("hide_break"))
        self.break_progress = None

    def show_calibration(self, progress: CalibrationProgress) -> None:
        self.calls.append(NotifierCall("show_calibration", progress))
        self.calibration = progress

    def hide_calibration(self) -> None:
        self.calls.append(NotifierCall("hide_calibration"))
        self.calibration = None

    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None:
        self.calls.append(NotifierCall("set_status", status))
        self.status = status
        self.blinks_per_minute = blinks_per_minute
