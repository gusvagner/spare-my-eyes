from collections.abc import Sequence

from spare_my_eyes.analysis.blink_detector import Blink, BlinkKind
from spare_my_eyes.capture.face_sample import FaceSample


def samples_from_ears(
    ears: Sequence[float],
    fps: float = 20.0,
    start: float = 0.0,
    iris_diameter_px: float = 11.0,
    head_yaw_degrees: float = 0.0,
) -> list[FaceSample]:
    return [
        FaceSample(
            timestamp=start + index / fps,
            face_present=True,
            left_ear=ear,
            right_ear=ear,
            iris_diameter_px=iris_diameter_px,
            head_yaw_degrees=head_yaw_degrees,
        )
        for index, ear in enumerate(ears)
    ]


def blink_of(kind: BlinkKind, ended_at: float = 0.0) -> Blink:
    return Blink(ended_at=ended_at, duration_seconds=0.15, min_ear_ratio=0.2, kind=kind)
