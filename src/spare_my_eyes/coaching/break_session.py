from dataclasses import dataclass
from enum import StrEnum
from typing import Self

_TOLERANCE = 1e-6


class BreakStep(StrEnum):
    LOOK_OUT = "look_out"
    SLOW_BLINKS = "slow_blinks"


class BreakOutcome(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True, slots=True)
class BreakTargets:
    gaze_seconds: float = 20.0
    slow_blinks: int = 5
    slow_blink_min_seconds: float = 0.3
    slow_blink_ear_ratio: float = 0.4
    inactivity_timeout_seconds: float = 120.0
    unverified_blink_seconds: float = 2.0


@dataclass(frozen=True, slots=True)
class BreakProgress:
    step: BreakStep
    gaze_seconds: float
    gaze_target_seconds: float
    slow_blinks: int
    slow_blink_target: int
    verified: bool


class BreakSession:
    """One combined break: look out the window, then a few slow, complete blinks."""

    MAX_SAMPLE_GAP_SECONDS = 1.0

    def __init__(self, started_at: float, targets: BreakTargets, *, verified: bool) -> None:
        self._targets = targets
        self._verified = verified
        self._step = BreakStep.LOOK_OUT
        self._outcome: BreakOutcome | None = None
        self._gaze_seconds = 0.0
        self._slow_blinks = 0
        self._paced_blink_seconds = 0.0
        self._closed_since: float | None = None
        self._last_timestamp: float | None = None
        self._last_activity_at = started_at

    @classmethod
    def verified_by_camera(cls, started_at: float, targets: BreakTargets) -> Self:
        return cls(started_at, targets, verified=True)

    @classmethod
    def on_honor_system(cls, started_at: float, targets: BreakTargets) -> Self:
        return cls(started_at, targets, verified=False)

    @property
    def outcome(self) -> BreakOutcome | None:
        return self._outcome

    @property
    def is_verified(self) -> bool:
        return self._verified

    def progress(self) -> BreakProgress:
        return BreakProgress(
            step=self._step,
            gaze_seconds=self._gaze_seconds,
            gaze_target_seconds=self._targets.gaze_seconds,
            slow_blinks=self._slow_blinks,
            slow_blink_target=self._targets.slow_blinks,
            verified=self._verified,
        )

    def observe(self, timestamp: float, looking_at_window: bool, ear_ratio: float | None) -> None:
        if self._outcome is not None:
            return
        elapsed = self._elapsed_until(timestamp)
        if self._step is BreakStep.LOOK_OUT:
            self._add_gaze(timestamp, elapsed if looking_at_window else 0.0)
            return
        self._track_slow_blink(timestamp, ear_ratio)

    def advance_unverified(self, now: float, user_is_idle: bool) -> None:
        if self._outcome is not None:
            return
        elapsed = self._elapsed_until(now)
        if not user_is_idle:
            return
        if self._step is BreakStep.LOOK_OUT:
            self._add_gaze(now, elapsed)
            return
        self._add_paced_blink_time(now, elapsed)

    def skip(self) -> None:
        if self._outcome is None:
            self._outcome = BreakOutcome.SKIPPED

    def check_timeout(self, now: float) -> None:
        if self._outcome is not None:
            return
        if now - self._last_activity_at >= self._targets.inactivity_timeout_seconds:
            self._outcome = BreakOutcome.TIMED_OUT

    def _elapsed_until(self, timestamp: float) -> float:
        previous, self._last_timestamp = self._last_timestamp, timestamp
        if previous is None:
            return 0.0
        return min(max(timestamp - previous, 0.0), self.MAX_SAMPLE_GAP_SECONDS)

    def _add_gaze(self, now: float, seconds: float) -> None:
        if seconds <= 0:
            return
        self._gaze_seconds = min(self._gaze_seconds + seconds, self._targets.gaze_seconds)
        self._last_activity_at = now
        if self._gaze_seconds >= self._targets.gaze_seconds - _TOLERANCE:
            self._gaze_seconds = self._targets.gaze_seconds
            self._step = BreakStep.SLOW_BLINKS

    def _track_slow_blink(self, timestamp: float, ear_ratio: float | None) -> None:
        if self._eyes_closed(ear_ratio):
            if self._closed_since is None:
                self._closed_since = timestamp
            return
        closed_since, self._closed_since = self._closed_since, None
        if closed_since is None:
            return
        if timestamp - closed_since >= self._targets.slow_blink_min_seconds - _TOLERANCE:
            self._count_slow_blink(timestamp)

    def _eyes_closed(self, ear_ratio: float | None) -> bool:
        return ear_ratio is not None and ear_ratio < self._targets.slow_blink_ear_ratio

    def _add_paced_blink_time(self, now: float, seconds: float) -> None:
        self._paced_blink_seconds += seconds
        if self._paced_blink_seconds < self._targets.unverified_blink_seconds - _TOLERANCE:
            return
        self._paced_blink_seconds = 0.0
        self._count_slow_blink(now)

    def _count_slow_blink(self, now: float) -> None:
        self._slow_blinks += 1
        self._last_activity_at = now
        if self._slow_blinks >= self._targets.slow_blinks:
            self._outcome = BreakOutcome.COMPLETED
