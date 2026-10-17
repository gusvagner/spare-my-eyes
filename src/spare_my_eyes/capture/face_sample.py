from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class FaceSample:
    timestamp: float
    face_present: bool
    left_ear: float = 0.0
    right_ear: float = 0.0
    iris_diameter_px: float = 0.0
    head_yaw_degrees: float = 0.0

    @property
    def mean_ear(self) -> float:
        return (self.left_ear + self.right_ear) / 2

    @classmethod
    def absent(cls, timestamp: float) -> Self:
        return cls(timestamp=timestamp, face_present=False)
