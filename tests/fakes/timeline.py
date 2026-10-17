from collections.abc import Callable

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.scripted import TimelineSegment, generate_samples
from tests.fakes.clock import FakeClock


class TimelineDriver:
    """Plays scripted face samples on a fake clock and ticks once per simulated second."""

    FPS = 20.0
    TICK_SECONDS = 1.0

    def __init__(
        self,
        clock: FakeClock,
        on_sample: Callable[[FaceSample], None],
        on_tick: Callable[[], None],
    ) -> None:
        self._clock = clock
        self._on_sample = on_sample
        self._on_tick = on_tick
        self._next_tick_at = clock.now()

    def play(self, *segments: TimelineSegment) -> None:
        start = self._clock.now()
        for sample in generate_samples(segments, self.FPS, start):
            self._clock.set(sample.timestamp)
            self._on_sample(sample)
            self._tick_when_due()
        self._clock.set(start + sum(segment.duration_seconds for segment in segments))

    def pass_time(self, seconds: int) -> None:
        for _ in range(seconds):
            self._clock.advance(self.TICK_SECONDS)
            self._tick_when_due()

    def _tick_when_due(self) -> None:
        if self._clock.now() + 1e-9 < self._next_tick_at:
            return
        self._on_tick()
        self._next_tick_at = self._clock.now() + self.TICK_SECONDS
