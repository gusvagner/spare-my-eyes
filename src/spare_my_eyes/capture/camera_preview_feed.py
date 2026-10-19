import threading
from dataclasses import dataclass

from spare_my_eyes.analysis.live_readout import LiveReading, LiveReadout
from spare_my_eyes.capture.face_detection import FaceDetection
from spare_my_eyes.capture.frame_source import Frame
from spare_my_eyes.capture.geometry import Point


@dataclass(frozen=True, slots=True)
class PreviewSnapshot:
    frame: Frame
    eye_points: tuple[Point, ...]
    reading: LiveReading
    captured_at: float


class CameraPreviewFeed:
    """Hands the newest frame from the capture thread to the camera window while it is open."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._readout: LiveReadout | None = None
        self._latest: PreviewSnapshot | None = None

    def start(self, readout: LiveReadout) -> None:
        with self._lock:
            self._readout = readout
            self._latest = None

    def stop(self) -> None:
        with self._lock:
            self._readout = None
            self._latest = None

    def publish(self, frame: Frame, detection: FaceDetection) -> None:
        with self._lock:
            if self._readout is None:
                return
            reading = self._readout.observe(detection.sample)
            captured_at = detection.sample.timestamp
            self._latest = PreviewSnapshot(frame, detection.eye_points, reading, captured_at)

    def latest(self) -> PreviewSnapshot | None:
        with self._lock:
            return self._latest
