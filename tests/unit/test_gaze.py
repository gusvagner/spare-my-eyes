import pytest

from spare_my_eyes.analysis.gaze import WindowGazeDetector, WindowSide
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import samples_from_ears


def turned(yaw: float) -> FaceSample:
    return samples_from_ears([0.3], head_yaw_degrees=yaw)[0]


@pytest.mark.parametrize(
    ("yaw", "expected"), [(-30.0, True), (-25.0, True), (-20.0, False), (30.0, False)]
)
def test_is_looking_at_window_left_side_requires_left_turn(yaw: float, expected: bool) -> None:
    assert WindowGazeDetector(WindowSide.LEFT).is_looking_at_window(turned(yaw)) is expected


@pytest.mark.parametrize(("yaw", "expected"), [(30.0, True), (20.0, False), (-30.0, False)])
def test_is_looking_at_window_right_side_requires_right_turn(yaw: float, expected: bool) -> None:
    assert WindowGazeDetector(WindowSide.RIGHT).is_looking_at_window(turned(yaw)) is expected


def test_is_looking_at_window_no_face_returns_false() -> None:
    assert not WindowGazeDetector(WindowSide.LEFT).is_looking_at_window(FaceSample.absent(0.0))
