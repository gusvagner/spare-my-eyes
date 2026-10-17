import pytest

from spare_my_eyes.calibration import CalibrationProgress, CalibrationStep
from spare_my_eyes.coaching.break_session import BreakProgress, BreakStep
from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.ui.notification_text import (
    describe_break,
    describe_calibration,
    describe_status,
    snooze_label,
)


def progress(step: BreakStep, gaze: float, blinks: int, verified: bool = True) -> BreakProgress:
    return BreakProgress(step, gaze, 20.0, blinks, 5, verified)


def test_describe_break_look_out_step_shows_gaze_seconds() -> None:
    text = describe_break(progress(BreakStep.LOOK_OUT, 7.4, 0))
    assert text.title == "Look out the window"
    assert text.detail == "7 / 20 s"
    assert text.fraction_done == pytest.approx(0.185)


def test_describe_break_slow_blink_step_shows_blink_count() -> None:
    text = describe_break(progress(BreakStep.SLOW_BLINKS, 20.0, 2))
    assert text.title == "5 slow, complete blinks"
    assert text.detail == "2 / 5"
    assert text.fraction_done == pytest.approx(0.7)


def test_describe_break_unverified_mentions_honor_system() -> None:
    text = describe_break(progress(BreakStep.LOOK_OUT, 0.0, 0, verified=False))
    assert "honor system" in text.detail


def test_describe_calibration_arm_length_step_shows_instruction_and_time() -> None:
    text = describe_calibration(CalibrationProgress(CalibrationStep.ARM_LENGTH, 4.2))
    assert "arm's length" in text.title
    assert text.detail == "4 s left"
    assert text.fraction_done == pytest.approx(0.58)


def test_describe_status_monitoring_with_rate_includes_rate() -> None:
    assert (
        describe_status(TrayStatus.MONITORING, 11.6) == "Spare My Eyes: monitoring, 12 blinks/min"
    )


def test_describe_status_no_camera_omits_rate() -> None:
    assert describe_status(TrayStatus.NO_CAMERA, 11.6) == "Spare My Eyes: no camera"


def test_snooze_label_default_snooze_reads_five_minutes() -> None:
    assert snooze_label(300.0) == "Snooze 5 min"
