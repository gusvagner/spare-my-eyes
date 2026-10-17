from pathlib import Path

import cv2
import numpy as np
import pytest

from spare_my_eyes.capture.mediapipe_landmarker import MediaPipeFaceLandmarker
from tests.integration.face_images import blank_frame, detect_once, load_face, shrink_into_canvas

pytestmark = pytest.mark.mediapipe


def test_detect_frontal_open_eyes_reports_open_ear_and_small_yaw() -> None:
    sample = detect_once(load_face("frontal_eyes_open.jpg"))
    assert sample.face_present
    assert 0.18 <= sample.mean_ear <= 0.45
    assert abs(sample.head_yaw_degrees) < 12.0
    assert sample.iris_diameter_px > 0.0


def test_detect_closed_eyes_reports_low_ear() -> None:
    sample = detect_once(load_face("frontal_eyes_closed.jpg"))
    assert sample.face_present
    assert sample.mean_ear < 0.15


def test_detect_head_turned_left_reports_negative_yaw() -> None:
    sample = detect_once(load_face("head_turned_left.jpg"))
    assert sample.face_present
    assert sample.head_yaw_degrees <= -15.0


def test_detect_head_turned_right_reports_positive_yaw() -> None:
    mirrored = np.ascontiguousarray(cv2.flip(load_face("head_turned_left.jpg"), 1), dtype=np.uint8)
    sample = detect_once(mirrored)
    assert sample.face_present
    assert sample.head_yaw_degrees >= 15.0


def test_detect_face_farther_away_reports_smaller_iris() -> None:
    near_frame = load_face("frontal_eyes_open.jpg")
    near = detect_once(near_frame)
    far = detect_once(shrink_into_canvas(near_frame, 0.5))
    assert far.face_present
    assert far.iris_diameter_px < near.iris_diameter_px * 0.7


def test_detect_blank_frame_reports_no_face() -> None:
    assert not detect_once(blank_frame()).face_present


def test_init_missing_model_raises_file_not_found_with_command(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"spare_my_eyes.model_asset"):
        MediaPipeFaceLandmarker(tmp_path / "missing.task")
