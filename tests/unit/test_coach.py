from dataclasses import dataclass

import pytest

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.coaching.coach import Coach
from spare_my_eyes.coaching.notifier import TrayStatus
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.policies import RecordingBreakControl, RecordingPolicy

SAMPLE = FaceSample(timestamp=0.0, face_present=True, left_ear=0.3, right_ear=0.3)


@dataclass
class CoachRig:
    coach: Coach
    policy: RecordingPolicy
    breaks: RecordingBreakControl
    notifier: RecordingNotifier
    clock: FakeClock


@pytest.fixture
def rig() -> CoachRig:
    clock = FakeClock()
    policy = RecordingPolicy()
    breaks = RecordingBreakControl()
    notifier = RecordingNotifier()
    coach = Coach([policy], breaks, lambda: 12.0, FakeIdleTimeProvider(4.0), notifier, clock)
    return CoachRig(coach, policy, breaks, notifier, clock)


def test_on_sample_forwards_to_policies_and_breaks(rig: CoachRig) -> None:
    rig.coach.on_sample(SAMPLE)
    assert rig.policy.samples == [SAMPLE]
    assert rig.breaks.samples == [SAMPLE]


def test_tick_forwards_time_and_idle_and_reports_monitoring(rig: CoachRig) -> None:
    rig.clock.advance(5.0)
    rig.coach.tick()
    assert rig.policy.ticks == [5.0]
    assert rig.breaks.ticks == [(5.0, 4.0)]
    assert rig.notifier.status is TrayStatus.MONITORING
    assert rig.notifier.blinks_per_minute == 12.0


def test_pause_for_suspends_everything_and_ignores_input(rig: CoachRig) -> None:
    rig.coach.pause_for(3600.0)
    rig.coach.on_sample(SAMPLE)
    rig.coach.tick()
    assert rig.policy.suspensions == 1
    assert "suspend" in rig.breaks.commands
    assert rig.policy.samples == []
    assert rig.policy.ticks == []
    assert rig.notifier.status is TrayStatus.PAUSED


def test_tick_after_pause_expires_resumes_monitoring(rig: CoachRig) -> None:
    rig.coach.pause_for(60.0)
    rig.clock.advance(60.0)
    rig.coach.tick()
    assert not rig.coach.is_paused
    assert rig.policy.ticks == [60.0]
    assert rig.notifier.status is TrayStatus.MONITORING


def test_on_camera_status_unavailable_switches_breaks_to_idle_time(rig: CoachRig) -> None:
    rig.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    assert rig.policy.suspensions == 1
    assert not rig.breaks.camera_active
    assert rig.notifier.status is TrayStatus.NO_CAMERA


def test_on_camera_status_busy_reports_paused(rig: CoachRig) -> None:
    rig.coach.on_camera_status(CameraStatus.BUSY)
    assert not rig.breaks.camera_active
    assert rig.notifier.status is TrayStatus.PAUSED


def test_on_camera_status_active_again_uses_camera(rig: CoachRig) -> None:
    rig.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    rig.coach.on_camera_status(CameraStatus.ACTIVE)
    assert rig.breaks.camera_active
    assert rig.notifier.status is TrayStatus.MONITORING


def test_break_commands_are_delegated(rig: CoachRig) -> None:
    rig.coach.start_break_now()
    rig.coach.snooze_break()
    rig.coach.skip_break()
    assert rig.breaks.commands == ["start_now", "snooze", "skip"]
