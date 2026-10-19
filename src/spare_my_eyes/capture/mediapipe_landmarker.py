from collections.abc import Sequence
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

from spare_my_eyes.capture.face_detection import FaceDetection
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.frame_source import Frame
from spare_my_eyes.capture.geometry import Point, eye_aspect_ratio, iris_diameter, yaw_degrees

RIGHT_EYE = (33, 160, 158, 133, 153, 144)
LEFT_EYE = (362, 385, 387, 263, 373, 380)
RIGHT_IRIS = (469, 470, 471, 472)
LEFT_IRIS = (474, 475, 476, 477)
PREVIEW_POINTS = RIGHT_EYE + LEFT_EYE + RIGHT_IRIS + LEFT_IRIS


class MediaPipeFaceLandmarker:
    def __init__(self, model_path: Path) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Face landmarker model not found at {model_path}; "
                "run `uv run python -m spare_my_eyes.model_asset`"
            )
        self._model_bytes = model_path.read_bytes()
        self._landmarker: FaceLandmarker | None = None
        self._last_timestamp_ms = -1

    def detect(self, frame: Frame, timestamp: float) -> FaceDetection:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        landmarker = self._open_landmarker()
        result = landmarker.detect_for_video(image, self._next_timestamp_ms(timestamp))
        if not result.face_landmarks:
            return FaceDetection(FaceSample.absent(timestamp))
        height, width = frame.shape[:2]
        landmarks = result.face_landmarks[0]
        points = [(float(mark.x) * width, float(mark.y) * height) for mark in landmarks]
        sample = _sample_from(points, result.facial_transformation_matrixes[0], timestamp)
        return FaceDetection(sample, tuple(_pick(points, PREVIEW_POINTS)))

    def close(self) -> None:
        if self._landmarker is None:
            return
        self._landmarker.close()
        self._landmarker = None

    def _open_landmarker(self) -> FaceLandmarker:
        if self._landmarker is None:
            self._landmarker = FaceLandmarker.create_from_options(_options(self._model_bytes))
            self._last_timestamp_ms = -1
        return self._landmarker

    def _next_timestamp_ms(self, timestamp: float) -> int:
        self._last_timestamp_ms = max(int(timestamp * 1000), self._last_timestamp_ms + 1)
        return self._last_timestamp_ms


def _options(model_bytes: bytes) -> FaceLandmarkerOptions:
    return FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_buffer=model_bytes),
        running_mode=RunningMode.VIDEO,
        num_faces=1,
        output_facial_transformation_matrixes=True,
    )


def _sample_from(points: Sequence[Point], matrix: object, timestamp: float) -> FaceSample:
    rotation = np.asarray(matrix, dtype=float)[:3, :3].tolist()
    left_iris = iris_diameter(_pick(points, LEFT_IRIS))
    right_iris = iris_diameter(_pick(points, RIGHT_IRIS))
    return FaceSample(
        timestamp=timestamp,
        face_present=True,
        left_ear=eye_aspect_ratio(_pick(points, LEFT_EYE)),
        right_ear=eye_aspect_ratio(_pick(points, RIGHT_EYE)),
        iris_diameter_px=(left_iris + right_iris) / 2,
        head_yaw_degrees=yaw_degrees(rotation),
    )


def _pick(points: Sequence[Point], indices: Sequence[int]) -> list[Point]:
    return [points[index] for index in indices]
