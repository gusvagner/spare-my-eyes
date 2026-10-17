import pytest

from spare_my_eyes.capture.camera_errors import CameraUnavailableError
from spare_my_eyes.capture.opencv_frame_source import OpenCvFrameSource

MISSING_CAMERA_INDEX = 99


def test_open_missing_camera_index_raises_camera_unavailable() -> None:
    with pytest.raises(CameraUnavailableError, match=str(MISSING_CAMERA_INDEX)):
        OpenCvFrameSource(MISSING_CAMERA_INDEX).open()


def test_read_before_open_raises_camera_unavailable() -> None:
    with pytest.raises(CameraUnavailableError, match="before open"):
        OpenCvFrameSource(0).read()


def test_close_without_open_does_nothing() -> None:
    OpenCvFrameSource(0).close()
