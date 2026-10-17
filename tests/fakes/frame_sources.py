import numpy as np

from spare_my_eyes.capture.frame_source import Frame


class FailingFrameSource:
    def __init__(
        self, open_error: Exception | None = None, read_error: Exception | None = None
    ) -> None:
        self._open_error = open_error
        self._read_error = read_error
        self.open_calls = 0
        self.close_calls = 0

    def open(self) -> None:
        self.open_calls += 1
        if self._open_error is not None:
            raise self._open_error

    def read(self) -> Frame:
        if self._read_error is not None:
            raise self._read_error
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def close(self) -> None:
        self.close_calls += 1


class StillImageFrameSource:
    def __init__(self, frame: Frame) -> None:
        self._frame = frame

    def open(self) -> None:
        return None

    def read(self) -> Frame:
        return self._frame.copy()

    def close(self) -> None:
        return None
