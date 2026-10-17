import math

import pytest

from spare_my_eyes.capture.geometry import eye_aspect_ratio, iris_diameter, yaw_degrees


def test_eye_aspect_ratio_open_eye_returns_height_over_twice_width() -> None:
    contour = [(0.0, 0.0), (1.0, -1.0), (3.0, -1.0), (4.0, 0.0), (3.0, 1.0), (1.0, 1.0)]
    assert eye_aspect_ratio(contour) == pytest.approx(0.5)


def test_eye_aspect_ratio_closed_eye_returns_zero() -> None:
    contour = [(0.0, 0.0), (1.0, 0.0), (3.0, 0.0), (4.0, 0.0), (3.0, 0.0), (1.0, 0.0)]
    assert eye_aspect_ratio(contour) == pytest.approx(0.0)


def test_eye_aspect_ratio_wrong_point_count_raises_value_error() -> None:
    with pytest.raises(ValueError, match="6 points"):
        eye_aspect_ratio([(0.0, 0.0)] * 5)


def test_eye_aspect_ratio_coincident_corners_raises_value_error() -> None:
    contour = [(2.0, 0.0), (1.0, -1.0), (3.0, -1.0), (2.0, 0.0), (3.0, 1.0), (1.0, 1.0)]
    with pytest.raises(ValueError, match="corners"):
        eye_aspect_ratio(contour)


def test_iris_diameter_circle_boundary_returns_diameter() -> None:
    boundary = [(15.0, 10.0), (10.0, 5.0), (5.0, 10.0), (10.0, 15.0)]
    assert iris_diameter(boundary) == pytest.approx(10.0)


def test_iris_diameter_wrong_point_count_raises_value_error() -> None:
    with pytest.raises(ValueError, match="4 points"):
        iris_diameter([(0.0, 0.0)] * 3)


@pytest.mark.parametrize("angle", [-40.0, 0.0, 30.0])
def test_yaw_degrees_rotation_about_vertical_axis_returns_angle(angle: float) -> None:
    radians = math.radians(angle)
    rotation = [
        [math.cos(radians), 0.0, math.sin(radians)],
        [0.0, 1.0, 0.0],
        [-math.sin(radians), 0.0, math.cos(radians)],
    ]
    assert yaw_degrees(rotation) == pytest.approx(angle)


def test_yaw_degrees_non_3x3_matrix_raises_value_error() -> None:
    with pytest.raises(ValueError, match="3x3"):
        yaw_degrees([[1.0, 0.0], [0.0, 1.0]])
