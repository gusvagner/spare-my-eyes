from dataclasses import dataclass

import pytest

from spare_my_eyes.analysis.blink_detector import BlinkDetector
from spare_my_eyes.analysis.blink_rate import BlinkRateMonitor
from spare_my_eyes.capture.scripted import OPEN_EAR, ScriptedBlink, TimelineSegment
from spare_my_eyes.coaching.blink_nudge import (
    BLINK_MESSAGE,
    SLOW_BLINK_MESSAGE,
    BlinkNudgePolicy,
    BlinkNudgeRules,
)
from tests.fakes.clock import FakeClock
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.timeline import TimelineDriver

LOW_RATE = 4.8


@dataclass
class NudgeRig:
    policy: BlinkNudgePolicy
    notifier: RecordingNotifier
    driver: TimelineDriver


@pytest.fixture
def rig() -> NudgeRig:
    clock = FakeClock()
    notifier = RecordingNotifier()
    policy = BlinkNudgePolicy(
        BlinkDetector(OPEN_EAR), BlinkRateMonitor(120.0), BlinkNudgeRules(), notifier
    )
    driver = TimelineDriver(clock, policy.on_sample, lambda: policy.on_tick(clock.now()))
    return NudgeRig(policy, notifier, driver)


def test_on_sample_low_rate_for_full_window_shows_blink_nudge(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.blink_nudge == BLINK_MESSAGE


def test_on_sample_normal_rate_shows_nothing(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(130.0, blinks_per_minute=15.0))
    assert rig.notifier.count("show_blink_nudge") == 0


def test_on_sample_low_rate_before_window_is_full_shows_nothing(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(60.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.blink_nudge is None


def test_on_sample_two_complete_blinks_hide_nudge(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.driver.play(TimelineSegment(0.5, blinks_per_minute=60.0))
    assert rig.notifier.blink_nudge == BLINK_MESSAGE
    rig.driver.play(TimelineSegment(0.5, blinks_per_minute=60.0))
    assert rig.notifier.blink_nudge is None


def test_on_sample_incomplete_blinks_do_not_hide_nudge(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.driver.play(TimelineSegment(3.0, blinks_per_minute=60.0, blink=ScriptedBlink.INCOMPLETE))
    assert rig.notifier.blink_nudge == BLINK_MESSAGE


def test_on_tick_nudge_visible_for_eight_seconds_hides_it(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.driver.play(TimelineSegment(9.0, blinks_per_minute=0.0))
    assert rig.notifier.blink_nudge is None


def test_on_sample_within_cooldown_does_not_show_again(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.driver.play(TimelineSegment(9.0, blinks_per_minute=0.0))
    rig.driver.play(TimelineSegment(170.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.count("show_blink_nudge") == 1
    rig.driver.play(TimelineSegment(15.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.count("show_blink_nudge") == 2


def test_on_sample_mostly_incomplete_blinks_uses_slow_blink_wording(rig: NudgeRig) -> None:
    rig.driver.play(
        TimelineSegment(121.0, blinks_per_minute=LOW_RATE, blink=ScriptedBlink.INCOMPLETE)
    )
    assert rig.notifier.blink_nudge == SLOW_BLINK_MESSAGE


def test_suspend_visible_nudge_hides_it_and_clears_window(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.policy.suspend()
    assert rig.notifier.blink_nudge is None
    rig.driver.play(TimelineSegment(60.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.blink_nudge is None


def test_current_rate_before_samples_returns_none(rig: NudgeRig) -> None:
    assert rig.policy.current_rate() is None


def test_current_rate_after_normal_blinking_reports_rate(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(60.0, blinks_per_minute=15.0))
    assert rig.policy.current_rate() == pytest.approx(15.0, abs=0.5)
