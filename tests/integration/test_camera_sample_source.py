from collections.abc import Iterator

import pytest

from spare_my_eyes.capture.camera_errors import CameraBusyError
from spare_my_eyes.capture.camera_preview_feed import CameraPreviewFeed
from spare_my_eyes.capture.camera_sample_source import CameraFaceSampleSource
from spare_my_eyes.capture.frame_source import FrameSource
from spare_my_eyes.capture.mediapipe_landmarker import MediaPipeFaceLandmarker
from spare_my_eyes.capture.source_factory import build_sample_source
from spare_my_eyes.model_asset import MODEL_PATH
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.frame_sources import FailingFrameSource, StillImageFrameSource
from tests.fakes.logs import RecordingLogHandler
from tests.integration.face_images import blank_frame, load_face

pytestmark = pytest.mark.mediapipe


def opened_source(frames: FrameSource, clock: FakeClock) -> Iterator[CameraFaceSampleSource]:
    source = CameraFaceSampleSource(
        frames, MediaPipeFaceLandmarker(MODEL_PATH), clock, CameraPreviewFeed()
    )
    source.open()
    try:
        yield source
    finally:
        source.close()


def test_next_sample_still_face_image_reports_face_with_clock_time() -> None:
    frames = StillImageFrameSource(load_face("frontal_eyes_open.jpg"))
    for source in opened_source(frames, FakeClock(42.0)):
        sample = source.next_sample()
        assert sample.face_present
        assert sample.timestamp == 42.0


def test_next_sample_blank_frame_reports_no_face() -> None:
    for source in opened_source(StillImageFrameSource(blank_frame()), FakeClock()):
        assert not source.next_sample().face_present


def test_next_sample_after_close_and_reopen_still_detects() -> None:
    for source in opened_source(StillImageFrameSource(blank_frame()), FakeClock()):
        source.next_sample()
        source.close()
        source.open()
        assert not source.next_sample().face_present


def test_next_sample_busy_camera_raises_camera_busy() -> None:
    frames = FailingFrameSource(read_error=CameraBusyError("in use by another app"))
    for source in opened_source(frames, FakeClock()):
        with pytest.raises(CameraBusyError):
            source.next_sample()


def test_build_sample_source_with_model_returns_camera_source(
    log_recorder: RecordingLogHandler,
) -> None:
    source = build_sample_source(
        None, Settings(), FakeClock(), CameraPreviewFeed(), log_recorder.logger
    )
    assert isinstance(source, CameraFaceSampleSource)
    source.close()
