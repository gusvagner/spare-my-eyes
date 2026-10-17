from typing import Protocol

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.frame_source import Frame


class FaceLandmarkDetector(Protocol):
    def detect(self, frame: Frame, timestamp: float) -> FaceSample: ...

    def close(self) -> None: ...
