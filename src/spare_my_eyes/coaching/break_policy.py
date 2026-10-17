import math
from dataclasses import dataclass

from spare_my_eyes.analysis.gaze import WindowGazeDetector
from spare_my_eyes.analysis.presence import PresenceTracker, PresenceUpdate
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.break_session import BreakSession, BreakTargets
from spare_my_eyes.coaching.notifier import Notifier
from spare_my_eyes.coaching.screen_time import ScreenTimeCounter

IDLE_LOOKING_AWAY_SECONDS = 3.0
RECENT_FACE_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class BreakSchedule:
    interval_seconds: float = 1200.0
    snooze_seconds: float = 300.0
    absence_reset_seconds: float = 300.0


class BreakPolicy:
    """Counts screen time from face or keyboard presence and runs one break at a time."""

    def __init__(
        self,
        schedule: BreakSchedule,
        targets: BreakTargets,
        gaze: WindowGazeDetector,
        presence: PresenceTracker,
        open_ear_baseline: float,
        notifier: Notifier,
        clock: Clock,
    ) -> None:
        self._schedule = schedule
        self._targets = targets
        self._gaze = gaze
        self._presence = presence
        self._open_ear_baseline = open_ear_baseline
        self._notifier = notifier
        self._clock = clock
        self._screen_time = ScreenTimeCounter()
        self._session: BreakSession | None = None
        self._snoozed_until = -math.inf
        self._camera_active = True
        self._last_face_seen_at: float | None = None

    @property
    def screen_time_seconds(self) -> float:
        return self._screen_time.seconds

    def on_sample(self, sample: FaceSample) -> None:
        if sample.face_present:
            self._last_face_seen_at = sample.timestamp
        session = self._session
        if session is None or not session.is_verified:
            return
        looking = self._gaze.is_looking_at_window(sample)
        session.observe(sample.timestamp, looking, self._ear_ratio(sample))
        self._publish()

    def on_tick(self, now: float, idle_seconds: float) -> None:
        self._track_presence(now, idle_seconds)
        if self._session is None:
            self._start_when_due(now)
            return
        self._advance(self._session, now, idle_seconds)

    def start_now(self) -> None:
        if self._session is None:
            self._start(self._clock.now())

    def snooze(self) -> None:
        if self._session is None:
            return
        self._dismiss_card()
        self._snoozed_until = self._clock.now() + self._schedule.snooze_seconds

    def skip(self) -> None:
        if self._session is None:
            return
        self._session.skip()
        self._publish()

    def suspend(self) -> None:
        self._dismiss_card()
        self._screen_time.reset()
        self._snoozed_until = -math.inf

    def use_camera(self) -> None:
        self._camera_active = True

    def use_idle_time(self) -> None:
        self._camera_active = False

    def _advance(self, session: BreakSession, now: float, idle_seconds: float) -> None:
        if not session.is_verified:
            session.advance_unverified(now, idle_seconds >= IDLE_LOOKING_AWAY_SECONDS)
        session.check_timeout(now)
        self._publish()

    def _track_presence(self, now: float, idle_seconds: float) -> None:
        update = self._presence.update(now, self._latest_sighting(now, idle_seconds))
        if self._is_long_absence(update):
            self._screen_time.reset()
        if update.present:
            self._screen_time.add_presence(now)
        else:
            self._screen_time.pause()

    def _is_long_absence(self, update: PresenceUpdate) -> bool:
        absence = update.returned_after_seconds
        return absence is not None and absence >= self._schedule.absence_reset_seconds

    def _latest_sighting(self, now: float, idle_seconds: float) -> float:
        last_input_at = now - idle_seconds
        if not self._camera_active or self._last_face_seen_at is None:
            return last_input_at
        return max(self._last_face_seen_at, last_input_at)

    def _start_when_due(self, now: float) -> None:
        if self._screen_time.seconds < self._schedule.interval_seconds:
            return
        if now < self._snoozed_until:
            return
        self._start(now)

    def _start(self, now: float) -> None:
        if self._camera_sees_user(now):
            self._session = BreakSession.verified_by_camera(now, self._targets)
        else:
            self._session = BreakSession.on_honor_system(now, self._targets)
        self._publish()

    def _camera_sees_user(self, now: float) -> bool:
        seen_at = self._last_face_seen_at
        return self._camera_active and seen_at is not None and now - seen_at < RECENT_FACE_SECONDS

    def _ear_ratio(self, sample: FaceSample) -> float | None:
        return sample.mean_ear / self._open_ear_baseline if sample.face_present else None

    def _publish(self) -> None:
        if self._session is None:
            return
        if self._session.outcome is None:
            self._notifier.show_break(self._session.progress())
            return
        self._finish()

    def _finish(self) -> None:
        self._dismiss_card()
        self._screen_time.reset()
        self._snoozed_until = -math.inf

    def _dismiss_card(self) -> None:
        if self._session is None:
            return
        self._session = None
        self._notifier.hide_break()
