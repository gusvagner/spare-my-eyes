from dataclasses import dataclass

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.geometry import Point


@dataclass(frozen=True, slots=True)
class FaceDetection:
    sample: FaceSample
    eye_points: tuple[Point, ...] = ()
