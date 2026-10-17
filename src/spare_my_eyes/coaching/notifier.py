from enum import StrEnum
from typing import Protocol

from spare_my_eyes.calibration import CalibrationProgress
from spare_my_eyes.coaching.break_session import BreakProgress


class TrayStatus(StrEnum):
    MONITORING = "monitoring"
    PAUSED = "paused"
    NO_CAMERA = "no_camera"
    CALIBRATING = "calibrating"


class Notifier(Protocol):
    def show_blink_nudge(self, message: str) -> None: ...

    def hide_blink_nudge(self) -> None: ...

    def show_distance_alert(self, message: str) -> None: ...

    def hide_distance_alert(self) -> None: ...

    def show_break(self, progress: BreakProgress) -> None: ...

    def hide_break(self) -> None: ...

    def show_calibration(self, progress: CalibrationProgress) -> None: ...

    def hide_calibration(self) -> None: ...

    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None: ...
