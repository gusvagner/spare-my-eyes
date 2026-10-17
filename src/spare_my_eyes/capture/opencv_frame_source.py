import cv2
import numpy as np

from spare_my_eyes.capture.camera_errors import CameraBusyError, CameraUnavailableError
from spare_my_eyes.capture.frame_source import Frame


class OpenCvFrameSource:
    def __init__(
        self, camera_index: int, width: int = 640, height: int = 480, fps: float = 20.0
    ) -> None:
        self._camera_index = camera_index
        self._width = width
        self._height = height
        self._fps = fps
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        capture = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            raise CameraUnavailableError(
                f"Camera {self._camera_index} could not be opened; "
                "expected a connected webcam at that index"
            )
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        capture.set(cv2.CAP_PROP_FPS, self._fps)
        self._capture = capture

    def read(self) -> Frame:
        if self._capture is None:
            raise CameraUnavailableError(f"Camera {self._camera_index} was read before open()")
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise CameraBusyError(
                f"Camera {self._camera_index} is open but returned no frame; "
                "another app may be using it"
            )
        return np.asarray(frame, dtype=np.uint8)

    def close(self) -> None:
        if self._capture is None:
            return
        self._capture.release()
        self._capture = None
