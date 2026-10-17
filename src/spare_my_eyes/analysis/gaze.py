from enum import StrEnum

from spare_my_eyes.capture.face_sample import FaceSample


class WindowSide(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class WindowGazeDetector:
    def __init__(self, side: WindowSide, min_yaw_degrees: float = 25.0) -> None:
        self._side = side
        self._min_yaw = min_yaw_degrees

    def is_looking_at_window(self, sample: FaceSample) -> bool:
        if not sample.face_present:
            return False
        if self._side is WindowSide.LEFT:
            return sample.head_yaw_degrees <= -self._min_yaw
        return sample.head_yaw_degrees >= self._min_yaw
