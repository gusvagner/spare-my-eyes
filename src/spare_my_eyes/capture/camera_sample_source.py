from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.frame_source import FrameSource
from spare_my_eyes.capture.landmarker import FaceLandmarkDetector
from spare_my_eyes.clock import Clock


class CameraFaceSampleSource:
    def __init__(self, frames: FrameSource, detector: FaceLandmarkDetector, clock: Clock) -> None:
        self._frames = frames
        self._detector = detector
        self._clock = clock

    def open(self) -> None:
        self._frames.open()

    def next_sample(self) -> FaceSample:
        frame = self._frames.read()
        return self._detector.detect(frame, self._clock.now())

    def close(self) -> None:
        self._frames.close()
        self._detector.close()
