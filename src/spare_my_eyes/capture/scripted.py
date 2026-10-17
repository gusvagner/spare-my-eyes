import itertools
import math
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from spare_my_eyes.capture.camera_errors import CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.clock import Clock

OPEN_EAR = 0.30
DEFAULT_IRIS_DIAMETER_PX = 11.0
_TOLERANCE = 1e-9


class ScriptedBlink(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    SLOW = "slow"


@dataclass(frozen=True, slots=True)
class _BlinkShape:
    duration_seconds: float
    ear_ratio: float


_SHAPES = {
    ScriptedBlink.COMPLETE: _BlinkShape(0.15, 0.2),
    ScriptedBlink.INCOMPLETE: _BlinkShape(0.15, 0.55),
    ScriptedBlink.SLOW: _BlinkShape(0.4, 0.2),
}


@dataclass(frozen=True, slots=True)
class TimelineSegment:
    duration_seconds: float
    blinks_per_minute: float = 15.0
    blink: ScriptedBlink = ScriptedBlink.COMPLETE
    face_present: bool = True
    head_yaw_degrees: float = 0.0
    iris_diameter_px: float = DEFAULT_IRIS_DIAMETER_PX


def generate_samples(
    segments: Iterable[TimelineSegment], fps: float = 20.0, start: float = 0.0
) -> Iterator[FaceSample]:
    segment_start = start
    for segment in segments:
        yield from _segment_samples(segment, fps, segment_start)
        segment_start += segment.duration_seconds


def _segment_samples(segment: TimelineSegment, fps: float, start: float) -> Iterator[FaceSample]:
    for index in range(round(segment.duration_seconds * fps)):
        offset = index / fps
        yield _sample_at(segment, start + offset, _blink_phase(offset, segment.blinks_per_minute))


def _blink_phase(offset: float, blinks_per_minute: float) -> float:
    if blinks_per_minute <= 0:
        return math.inf
    return offset % (60.0 / blinks_per_minute)


def _sample_at(segment: TimelineSegment, timestamp: float, phase: float) -> FaceSample:
    if not segment.face_present:
        return FaceSample.absent(timestamp)
    shape = _SHAPES[segment.blink]
    ratio = shape.ear_ratio if phase < shape.duration_seconds - _TOLERANCE else 1.0
    ear = OPEN_EAR * ratio
    return FaceSample(
        timestamp=timestamp,
        face_present=True,
        left_ear=ear,
        right_ear=ear,
        iris_diameter_px=segment.iris_diameter_px,
        head_yaw_degrees=segment.head_yaw_degrees,
    )


class ScriptedFaceSampleSource:
    """Replays a scripted timeline in real time, for demos and the app smoke test."""

    def __init__(
        self,
        segments: Sequence[TimelineSegment],
        fps: float,
        clock: Clock,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not segments:
            raise ValueError(f"Scripted timeline needs at least one segment, got {segments!r}")
        self._segments = tuple(segments)
        self._fps = fps
        self._clock = clock
        self._sleep = sleep
        self._samples: Iterator[FaceSample] | None = None

    def open(self) -> None:
        self._samples = generate_samples(itertools.cycle(self._segments), self._fps)

    def next_sample(self) -> FaceSample:
        if self._samples is None:
            raise CameraUnavailableError("Scripted source was read before open()")
        self._sleep(1.0 / self._fps)
        return replace(next(self._samples), timestamp=self._clock.now())

    def close(self) -> None:
        self._samples = None
