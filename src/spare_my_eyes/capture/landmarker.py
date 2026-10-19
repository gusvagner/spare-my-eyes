from typing import Protocol

from spare_my_eyes.capture.face_detection import FaceDetection
from spare_my_eyes.capture.frame_source import Frame


class FaceLandmarkDetector(Protocol):
    def detect(self, frame: Frame, timestamp: float) -> FaceDetection: ...

    def close(self) -> None: ...
