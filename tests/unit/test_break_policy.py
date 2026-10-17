from dataclasses import dataclass

import pytest

from spare_my_eyes.analysis.gaze import WindowGazeDetector, WindowSide
from spare_my_eyes.analysis.presence import PresenceTracker
from spare_my_eyes.capture.scripted import OPEN_EAR, ScriptedBlink, TimelineSegment
from spare_my_eyes.coaching.break_policy import BreakPolicy, BreakSchedule
from spare_my_eyes.coaching.break_session import BreakStep, BreakTargets
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.timeline import TimelineDriver

INTERVAL = 300.0
USER_NOT_TYPING = 10_000.0


@dataclass
class BreakRig:
    policy: BreakPolicy
    notifier: RecordingNotifier
    idle: FakeIdleTimeProvider
    driver: TimelineDriver


@pytest.fixture
def rig() -> BreakRig:
    clock = FakeClock()
    notifier = RecordingNotifier()
    idle = FakeIdleTimeProvider(USER_NOT_TYPING)
    schedule = BreakSchedule(interval_seconds=INTERVAL, snooze_seconds=30.0)
    policy = BreakPolicy(
        schedule,
        BreakTargets(),
        WindowGazeDetector(WindowSide.LEFT),
        PresenceTracker(60.0),
        OPEN_EAR,
        notifier,
        clock,
    )
    driver = TimelineDriver(
        clock, policy.on_sample, lambda: policy.on_tick(clock.now(), idle.idle_seconds())
    )
    return BreakRig(policy, notifier, idle, driver)


def test_on_tick_before_interval_shows_nothing(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL - 2.0))
    assert rig.notifier.break_progress is None


def test_on_tick_screen_time_reaches_interval_shows_verified_break(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    progress = rig.notifier.break_progress
    assert progress is not None
    assert progress.step is BreakStep.LOOK_OUT
    assert progress.verified


def test_on_sample_gaze_then_slow_blinks_complete_break_and_reset_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    rig.driver.play(TimelineSegment(21.0, head_yaw_degrees=-30.0))
    rig.driver.play(TimelineSegment(10.5, blinks_per_minute=30.0, blink=ScriptedBlink.SLOW))
    assert rig.notifier.break_progress is None
    assert rig.policy.screen_time_seconds < 15.0


def test_snooze_open_break_hides_it_until_snooze_ends(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    rig.policy.snooze()
    assert rig.notifier.break_progress is None
    rig.driver.play(TimelineSegment(28.0))
    assert rig.notifier.break_progress is None
    rig.driver.play(TimelineSegment(4.0))
    assert rig.notifier.break_progress is not None


def test_skip_open_break_hides_it_and_resets_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    rig.policy.skip()
    assert rig.notifier.break_progress is None
    assert rig.policy.screen_time_seconds == 0.0


def test_on_tick_no_face_but_user_typing_starts_unverified_break(rig: BreakRig) -> None:
    rig.idle.seconds = 0.0
    rig.driver.play(TimelineSegment(INTERVAL + 2.0, face_present=False))
    progress = rig.notifier.break_progress
    assert progress is not None
    assert not progress.verified


def test_on_tick_absence_shorter_than_five_minutes_pauses_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(100.0))
    rig.driver.play(TimelineSegment(200.0, face_present=False))
    rig.driver.play(TimelineSegment(10.0))
    assert rig.policy.screen_time_seconds == pytest.approx(170.0, abs=3.0)


def test_on_tick_absence_of_five_minutes_resets_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(100.0))
    rig.driver.play(TimelineSegment(301.0, face_present=False))
    rig.driver.play(TimelineSegment(10.0))
    assert rig.policy.screen_time_seconds < 15.0


def test_suspend_open_break_hides_it_and_resets_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    rig.policy.suspend()
    assert rig.notifier.break_progress is None
    assert rig.policy.screen_time_seconds == 0.0


def test_use_idle_time_camera_off_runs_unverified_break_from_input(rig: BreakRig) -> None:
    rig.policy.use_idle_time()
    rig.idle.seconds = 0.0
    rig.driver.pass_time(int(INTERVAL) + 2)
    progress = rig.notifier.break_progress
    assert progress is not None
    assert not progress.verified


def test_start_now_shows_break_immediately(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(5.0))
    rig.policy.start_now()
    assert rig.notifier.break_progress is not None
