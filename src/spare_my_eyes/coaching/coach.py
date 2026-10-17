from collections.abc import Callable, Sequence
from typing import Protocol

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.notifier import Notifier, TrayStatus
from spare_my_eyes.system.idle_time import IdleTimeProvider


class CoachingPolicy(Protocol):
    def on_sample(self, sample: FaceSample) -> None: ...

    def on_tick(self, now: float) -> None: ...

    def suspend(self) -> None: ...


class BreakControl(Protocol):
    def on_sample(self, sample: FaceSample) -> None: ...

    def on_tick(self, now: float, idle_seconds: float) -> None: ...

    def start_now(self) -> None: ...

    def snooze(self) -> None: ...

    def skip(self) -> None: ...

    def suspend(self) -> None: ...

    def use_camera(self) -> None: ...

    def use_idle_time(self) -> None: ...


class Coach:
    """Feeds samples and ticks to the coaching policies and reports the tray status."""

    def __init__(
        self,
        camera_policies: Sequence[CoachingPolicy],
        breaks: BreakControl,
        blink_rate: Callable[[], float | None],
        idle: IdleTimeProvider,
        notifier: Notifier,
        clock: Clock,
    ) -> None:
        self._camera_policies = tuple(camera_policies)
        self._breaks = breaks
        self._blink_rate = blink_rate
        self._idle = idle
        self._notifier = notifier
        self._clock = clock
        self._camera_status = CameraStatus.ACTIVE
        self._paused_until: float | None = None

    @property
    def is_paused(self) -> bool:
        return self._paused_until is not None

    def on_sample(self, sample: FaceSample) -> None:
        if self.is_paused:
            return
        for policy in self._camera_policies:
            policy.on_sample(sample)
        self._breaks.on_sample(sample)

    def tick(self) -> None:
        now = self._clock.now()
        self._resume_when_due(now)
        if not self.is_paused:
            self._tick_policies(now)
        self._report_status()

    def pause_for(self, seconds: float) -> None:
        self._paused_until = self._clock.now() + seconds
        self.suspend()
        self._report_status()

    def suspend(self) -> None:
        self._suspend_camera_policies()
        self._breaks.suspend()

    def resume(self) -> None:
        self._paused_until = None
        self._report_status()

    def pause_remaining(self) -> float | None:
        if self._paused_until is None:
            return None
        return max(0.0, self._paused_until - self._clock.now())

    def on_camera_status(self, status: CameraStatus) -> None:
        self._camera_status = status
        if status is CameraStatus.ACTIVE:
            self._breaks.use_camera()
        else:
            self._suspend_camera_policies()
            self._breaks.use_idle_time()
        self._report_status()

    def start_break_now(self) -> None:
        self._paused_until = None
        self._breaks.start_now()

    def snooze_break(self) -> None:
        self._breaks.snooze()

    def skip_break(self) -> None:
        self._breaks.skip()

    def _tick_policies(self, now: float) -> None:
        for policy in self._camera_policies:
            policy.on_tick(now)
        self._breaks.on_tick(now, self._idle.idle_seconds())

    def _resume_when_due(self, now: float) -> None:
        if self._paused_until is not None and now >= self._paused_until:
            self._paused_until = None

    def _suspend_camera_policies(self) -> None:
        for policy in self._camera_policies:
            policy.suspend()

    def _status(self) -> TrayStatus:
        if self.is_paused or self._camera_status is CameraStatus.BUSY:
            return TrayStatus.PAUSED
        if self._camera_status is CameraStatus.UNAVAILABLE:
            return TrayStatus.NO_CAMERA
        return TrayStatus.MONITORING

    def _report_status(self) -> None:
        self._notifier.set_status(self._status(), self._blink_rate())
