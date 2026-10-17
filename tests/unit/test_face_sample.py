import pytest

from spare_my_eyes.capture.face_sample import FaceSample


def test_mean_ear_two_eyes_returns_average() -> None:
    sample = FaceSample(timestamp=1.0, face_present=True, left_ear=0.2, right_ear=0.3)
    assert sample.mean_ear == pytest.approx(0.25)


def test_absent_any_timestamp_has_no_face_and_zero_measurements() -> None:
    assert FaceSample.absent(5.0) == FaceSample(timestamp=5.0, face_present=False)
