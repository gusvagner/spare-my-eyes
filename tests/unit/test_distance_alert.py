from dataclasses import dataclass

import pytest

from spare_my_eyes.analysis.distance import ScreenDistanceEstimator
from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.cooldown import Cooldown
from spare_my_eyes.coaching.distance_alert import MOVE_BACK_MESSAGE, DistanceAlertPolicy
from tests.fakes.clock import FakeClock
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.timeline import TimelineDriver

FOCAL_SCALE = 660.0


def at_cm(duration: float, centimeters: float) -> TimelineSegment:
    return TimelineSegment(duration, iris_diameter_px=FOCAL_SCALE / centimeters)


@dataclass
class DistanceRig:
    policy: DistanceAlertPolicy
    notifier: RecordingNotifier
    driver: TimelineDriver


@pytest.fixture
def rig() -> DistanceRig:
    clock = FakeClock()
    notifier = RecordingNotifier()
    policy = DistanceAlertPolicy(ScreenDistanceEstimator(FOCAL_SCALE), Cooldown(300.0), notifier)
    driver = TimelineDriver(clock, policy.on_sample, lambda: policy.on_tick(clock.now()))
    return DistanceRig(policy, notifier, driver)


def test_on_sample_far_from_screen_shows_nothing(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(60.0, 60.0))
    assert rig.notifier.distance_alert is None


def test_on_sample_close_for_less_than_thirty_seconds_shows_nothing(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(29.0, 45.0))
    assert rig.notifier.distance_alert is None


def test_on_sample_close_for_thirty_seconds_shows_alert(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(31.0, 45.0))
    assert rig.notifier.distance_alert == MOVE_BACK_MESSAGE


def test_on_sample_between_thresholds_keeps_alert_until_clear(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(31.0, 45.0))
    rig.driver.play(at_cm(10.0, 52.0))
    assert rig.notifier.distance_alert == MOVE_BACK_MESSAGE
    rig.driver.play(at_cm(5.0, 58.0))
    assert rig.notifier.distance_alert is None


def test_on_sample_close_again_within_cooldown_waits_for_cooldown(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(31.0, 45.0))
    rig.driver.play(at_cm(5.0, 58.0))
    rig.driver.play(at_cm(60.0, 45.0))
    assert rig.notifier.distance_alert is None
    rig.driver.play(at_cm(250.0, 45.0))
    assert rig.notifier.count("show_distance_alert") == 2


def test_suspend_visible_alert_hides_it_and_restarts_hold(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(31.0, 45.0))
    rig.policy.suspend()
    assert rig.notifier.distance_alert is None
    rig.driver.play(at_cm(10.0, 45.0))
    assert rig.notifier.distance_alert is None
