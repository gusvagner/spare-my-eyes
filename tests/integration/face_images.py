from pathlib import Path

import cv2
import numpy as np
import pytest

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.frame_source import Frame
from spare_my_eyes.capture.mediapipe_landmarker import MediaPipeFaceLandmarker
from spare_my_eyes.model_asset import MODEL_PATH

FACES_DIR = Path(__file__).parent.parent / "fixtures" / "faces"
FRAME_WIDTH = 640


def load_face(name: str) -> Frame:
    path = FACES_DIR / name
    if not path.is_file():
        pytest.skip(f"Fixture {name} is missing; see tests/fixtures/CREDITS.md")
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"{path} is not a readable image; expected a JPEG or PNG file")
    scale = FRAME_WIDTH / image.shape[1]
    resized = cv2.resize(image, (FRAME_WIDTH, round(image.shape[0] * scale)))
    return np.asarray(resized, dtype=np.uint8)


def blank_frame() -> Frame:
    return np.full((480, FRAME_WIDTH, 3), 128, dtype=np.uint8)


def shrink_into_canvas(frame: Frame, factor: float) -> Frame:
    small = cv2.resize(frame, None, fx=factor, fy=factor)
    canvas = np.full_like(frame, 128)
    canvas[: small.shape[0], : small.shape[1]] = small
    return canvas


def detect_once(frame: Frame) -> FaceSample:
    if not MODEL_PATH.is_file():
        pytest.fail(
            f"Model missing at {MODEL_PATH}; run `uv run python -m spare_my_eyes.model_asset`"
        )
    landmarker = MediaPipeFaceLandmarker(MODEL_PATH)
    try:
        return landmarker.detect(frame, 0.0)
    finally:
        landmarker.close()
