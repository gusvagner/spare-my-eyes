import numpy as np

from spare_my_eyes.capture.camera_preview_feed import CameraPreviewFeed
from spare_my_eyes.capture.camera_sample_source import CameraFaceSampleSource
from spare_my_eyes.capture.face_detection import FaceDetection
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.coaching.factory import build_live_readout
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.frame_sources import StillImageFrameSource
from tests.fakes.landmarkers import EYE_POINTS, FixedFaceLandmarker

FRAME = np.full((48, 64, 3), 90, dtype=np.uint8)
DETECTION = FaceDetection(FaceSample(3.0, True, 0.28, 0.28, 11.0, 0.0), EYE_POINTS)


def started_feed() -> CameraPreviewFeed:
    feed = CameraPreviewFeed()
    feed.start(build_live_readout(Settings()))
    return feed


def test_publish_before_start_keeps_nothing() -> None:
    feed = CameraPreviewFeed()
    feed.publish(FRAME, DETECTION)
    assert feed.latest() is None


def test_publish_after_start_keeps_frame_points_and_reading() -> None:
    feed = started_feed()
    feed.publish(FRAME, DETECTION)
    snapshot = feed.latest()
    assert snapshot is not None
    assert snapshot.frame is FRAME
    assert snapshot.eye_points == EYE_POINTS
    assert snapshot.reading.face_present
    assert snapshot.captured_at == 3.0


def test_stop_drops_the_last_snapshot_and_ignores_new_frames() -> None:
    feed = started_feed()
    feed.publish(FRAME, DETECTION)
    feed.stop()
    feed.publish(FRAME, DETECTION)
    assert feed.latest() is None


def test_next_sample_with_started_feed_publishes_the_camera_frame() -> None:
    feed = started_feed()
    source = CameraFaceSampleSource(
        StillImageFrameSource(FRAME), FixedFaceLandmarker(), FakeClock(7.0), feed
    )
    sample = source.next_sample()
    snapshot = feed.latest()
    assert sample.timestamp == 7.0
    assert snapshot is not None and snapshot.eye_points == EYE_POINTS
