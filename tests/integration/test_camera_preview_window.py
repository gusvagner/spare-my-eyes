import tkinter as tk
from collections.abc import Iterator

import numpy as np
import pytest

from spare_my_eyes.capture.camera_preview_feed import CameraPreviewFeed
from spare_my_eyes.capture.face_detection import FaceDetection
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.settings import Settings
from spare_my_eyes.ui.camera_preview_window import CameraPreviewOpener, CameraPreviewWindow
from spare_my_eyes.ui.preview_text import WAITING_FOR_CAMERA
from tests.fakes.clock import FakeClock
from tests.fakes.landmarkers import EYE_POINTS

pytestmark = pytest.mark.gui

FRAME = np.zeros((480, 640, 3), dtype=np.uint8)


def detection_at(timestamp: float) -> FaceDetection:
    return FaceDetection(FaceSample(timestamp, True, 0.28, 0.28, 11.0, 0.0), EYE_POINTS)


@pytest.fixture
def opener(tk_root: tk.Tk) -> Iterator[CameraPreviewOpener]:
    preview = CameraPreviewOpener(tk_root, CameraPreviewFeed(), Settings, FakeClock(10.0))
    yield preview
    if preview.current is not None and preview.current.is_open:
        preview.current.close()


def opened_window(opener: CameraPreviewOpener) -> CameraPreviewWindow:
    opener()
    assert opener.current is not None
    return opener.current


def test_refresh_without_frames_shows_waiting_message(opener: CameraPreviewOpener) -> None:
    window = opened_window(opener)
    window.refresh()
    assert window.readout_label.cget("text") == WAITING_FOR_CAMERA


def test_refresh_with_recent_frame_shows_image_and_readings(
    opener: CameraPreviewOpener,
) -> None:
    window = opened_window(opener)
    opener.feed.publish(FRAME, detection_at(9.5))
    window.refresh()
    assert "Face: detected" in str(window.readout_label.cget("text"))
    assert window.image_label.cget("image") != ""


def test_refresh_with_stale_frame_shows_waiting_message(opener: CameraPreviewOpener) -> None:
    window = opened_window(opener)
    opener.feed.publish(FRAME, detection_at(5.0))
    window.refresh()
    assert window.readout_label.cget("text") == WAITING_FOR_CAMERA


def test_close_stops_the_feed(opener: CameraPreviewOpener) -> None:
    window = opened_window(opener)
    window.close()
    opener.feed.publish(FRAME, detection_at(9.5))
    assert not window.is_open
    assert opener.feed.latest() is None


def test_opener_second_call_reuses_open_window(opener: CameraPreviewOpener) -> None:
    first = opened_window(opener)
    opener()
    assert opener.current is first
