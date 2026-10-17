import pytest

from spare_my_eyes.analysis.distance import (
    DistanceReading,
    ScreenDistanceEstimator,
    focal_scale_from_calibration,
)
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import samples_from_ears

FOCAL_SCALE = 660.0
FPS = 20.0


def at_distance(
    estimator: ScreenDistanceEstimator, centimeters: float, start: float, end: float
) -> DistanceReading | None:
    count = round((end - start) * FPS) + 1
    iris = FOCAL_SCALE / centimeters
    reading = None
    for sample in samples_from_ears([0.3] * count, fps=FPS, start=start, iris_diameter_px=iris):
        reading = estimator.update(sample)
    return reading


def test_focal_scale_from_calibration_arm_length_iris_returns_scale() -> None:
    assert focal_scale_from_calibration(11.0) == pytest.approx(660.0)


def test_update_far_face_reports_distance_and_not_too_close() -> None:
    reading = at_distance(ScreenDistanceEstimator(FOCAL_SCALE), 60.0, 0.0, 0.0)
    assert reading is not None
    assert reading.distance_cm == pytest.approx(60.0)
    assert not reading.too_close


def test_update_close_for_less_than_hold_is_not_too_close() -> None:
    reading = at_distance(ScreenDistanceEstimator(FOCAL_SCALE), 45.0, 0.0, 29.9)
    assert reading is not None and not reading.too_close


def test_update_close_for_hold_seconds_reports_too_close() -> None:
    reading = at_distance(ScreenDistanceEstimator(FOCAL_SCALE), 45.0, 0.0, 30.0)
    assert reading is not None and reading.too_close


def test_update_between_thresholds_after_too_close_stays_too_close() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 45.0, 0.0, 30.0)
    reading = at_distance(estimator, 52.0, 30.05, 35.0)
    assert reading is not None and reading.too_close


def test_update_beyond_clear_distance_clears_too_close() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 45.0, 0.0, 30.0)
    reading = at_distance(estimator, 58.0, 30.05, 35.0)
    assert reading is not None and not reading.too_close


def test_update_brief_move_back_restarts_hold() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 45.0, 0.0, 20.0)
    at_distance(estimator, 60.0, 20.05, 21.0)
    reading = at_distance(estimator, 45.0, 21.05, 45.0)
    assert reading is not None and not reading.too_close


def test_update_single_outlier_is_smoothed_by_median() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 60.0, 0.0, 5.0)
    outlier = samples_from_ears([0.3], start=5.05, iris_diameter_px=30.0)[0]
    reading = estimator.update(outlier)
    assert reading is not None
    assert reading.distance_cm == pytest.approx(60.0, rel=0.01)


def test_update_absent_face_returns_none() -> None:
    assert ScreenDistanceEstimator(FOCAL_SCALE).update(FaceSample.absent(1.0)) is None


def test_reset_clears_too_close_state() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 45.0, 0.0, 30.0)
    estimator.reset()
    reading = at_distance(estimator, 45.0, 30.05, 30.05)
    assert reading is not None and not reading.too_close


def test_init_non_positive_focal_scale_raises_value_error() -> None:
    with pytest.raises(ValueError, match="focal_scale"):
        ScreenDistanceEstimator(0.0)
