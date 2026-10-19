import pytest

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.analysis.live_readout import LiveReading, LiveReadout
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.coaching.factory import build_live_readout
from spare_my_eyes.settings import Settings
from tests.fakes.samples import samples_from_ears

OPEN_EAR = 0.28
SETTINGS = Settings(window_side=WindowSide.LEFT, open_ear_baseline=OPEN_EAR, focal_scale=660.0)


def observe_all(readout: LiveReadout, samples: list[FaceSample]) -> LiveReading:
    reading = None
    for sample in samples:
        reading = readout.observe(sample)
    assert reading is not None
    return reading


def test_observe_full_blink_counts_one_complete_blink() -> None:
    ears = [OPEN_EAR] * 5 + [0.05] * 3 + [OPEN_EAR] * 5
    reading = observe_all(build_live_readout(SETTINGS), samples_from_ears(ears))
    assert (reading.complete_blinks, reading.incomplete_blinks) == (1, 0)


def test_observe_half_blink_counts_one_incomplete_blink() -> None:
    ears = [OPEN_EAR] * 5 + [0.18] * 3 + [OPEN_EAR] * 5
    reading = observe_all(build_live_readout(SETTINGS), samples_from_ears(ears))
    assert (reading.complete_blinks, reading.incomplete_blinks) == (0, 1)


def test_observe_open_eyes_reports_openness_relative_to_calibration() -> None:
    reading = observe_all(build_live_readout(SETTINGS), samples_from_ears([0.14]))
    assert reading.eye_openness == pytest.approx(0.5)


def test_observe_iris_size_reports_distance_in_cm() -> None:
    samples = samples_from_ears([OPEN_EAR], iris_diameter_px=11.0)
    reading = observe_all(build_live_readout(SETTINGS), samples)
    assert reading.distance_cm == pytest.approx(60.0)


def test_observe_head_turned_to_window_side_reports_looking_at_window() -> None:
    samples = samples_from_ears([OPEN_EAR], head_yaw_degrees=-30.0)
    reading = observe_all(build_live_readout(SETTINGS), samples)
    assert reading.looking_at_window
    assert reading.head_yaw_degrees == -30.0


def test_observe_head_turned_away_from_window_reports_not_looking() -> None:
    samples = samples_from_ears([OPEN_EAR], head_yaw_degrees=30.0)
    assert not observe_all(build_live_readout(SETTINGS), samples).looking_at_window


def test_observe_no_face_reports_absent_without_distance() -> None:
    reading = build_live_readout(SETTINGS).observe(FaceSample.absent(1.0))
    assert not reading.face_present
    assert reading.distance_cm is None


def test_observe_uncalibrated_settings_uses_default_baseline() -> None:
    reading = observe_all(build_live_readout(Settings()), samples_from_ears([0.28]))
    assert reading.eye_openness == pytest.approx(1.0)
