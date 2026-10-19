from spare_my_eyes.capture.face_detection import FaceDetection
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.frame_source import Frame

EYE_POINTS = ((100.0, 120.0), (140.0, 118.0))


class FixedFaceLandmarker:
    def __init__(self, eye_points: tuple[tuple[float, float], ...] = EYE_POINTS) -> None:
        self._eye_points = eye_points
        self.closed = False

    def detect(self, frame: Frame, timestamp: float) -> FaceDetection:
        sample = FaceSample(timestamp, True, 0.28, 0.28, 11.0, 0.0)
        return FaceDetection(sample, self._eye_points)

    def close(self) -> None:
        self.closed = True
