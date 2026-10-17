from dataclasses import dataclass

from spare_my_eyes.calibration import CalibrationProgress, CalibrationSession, CalibrationStep
from spare_my_eyes.coaching.break_session import BreakProgress, BreakStep
from spare_my_eyes.coaching.notifier import TrayStatus

LOOK_OUT_TITLE = "Look out the window"
HONOR_SYSTEM_NOTE = "camera off, honor system"
SKIP_LABEL = "Skip"

_CALIBRATION_TITLES = {
    CalibrationStep.LOOK_AT_SCREEN: "Look at the screen as you normally do",
    CalibrationStep.ARM_LENGTH: "Sit at arm's length from the screen (about 60 cm)",
    CalibrationStep.DONE: "Calibration done",
}

_STATUS_LABELS = {
    TrayStatus.MONITORING: "monitoring",
    TrayStatus.PAUSED: "paused",
    TrayStatus.NO_CAMERA: "no camera",
    TrayStatus.CALIBRATING: "calibrating",
}


@dataclass(frozen=True, slots=True)
class CardText:
    title: str
    detail: str
    fraction_done: float


def describe_break(progress: BreakProgress) -> CardText:
    fraction = _break_fraction(progress)
    if progress.step is BreakStep.LOOK_OUT:
        detail = f"{progress.gaze_seconds:.0f} / {progress.gaze_target_seconds:.0f} s"
        return CardText(LOOK_OUT_TITLE, _with_note(detail, progress), fraction)
    title = f"{progress.slow_blink_target} slow, complete blinks"
    detail = f"{progress.slow_blinks} / {progress.slow_blink_target}"
    return CardText(title, _with_note(detail, progress), fraction)


def describe_calibration(progress: CalibrationProgress) -> CardText:
    fraction = 1.0 - progress.seconds_left / CalibrationSession.STEP_SECONDS
    detail = f"{progress.seconds_left:.0f} s left"
    return CardText(_CALIBRATION_TITLES[progress.step], detail, fraction)


def describe_status(status: TrayStatus, blinks_per_minute: float | None) -> str:
    label = f"Spare My Eyes: {_STATUS_LABELS[status]}"
    if blinks_per_minute is None or status is not TrayStatus.MONITORING:
        return label
    return f"{label}, {blinks_per_minute:.0f} blinks/min"


def snooze_label(snooze_seconds: float) -> str:
    return f"Snooze {snooze_seconds / 60:.0f} min"


def _break_fraction(progress: BreakProgress) -> float:
    gaze = min(progress.gaze_seconds / progress.gaze_target_seconds, 1.0)
    blinks = min(progress.slow_blinks / progress.slow_blink_target, 1.0)
    return 0.5 * gaze + 0.5 * blinks


def _with_note(detail: str, progress: BreakProgress) -> str:
    return detail if progress.verified else f"{detail} ({HONOR_SYSTEM_NOTE})"
