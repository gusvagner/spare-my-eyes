from spare_my_eyes.capture.scripted import ScriptedBlink, TimelineSegment
from spare_my_eyes.coaching.blink_nudge import BLINK_MESSAGE, SLOW_BLINK_MESSAGE
from tests.integration.pipeline_run import PipelineRun

LOW_RATE = 4.8


def test_blink_nudge_low_rate_shows_then_two_complete_blinks_hide_it() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    assert run.notifier.blink_nudge == BLINK_MESSAGE
    run.play(TimelineSegment(0.5, blinks_per_minute=60.0))
    assert run.notifier.blink_nudge == BLINK_MESSAGE
    run.play(TimelineSegment(0.5, blinks_per_minute=60.0))
    assert run.notifier.blink_nudge is None


def test_blink_nudge_after_hiding_respects_three_minute_cooldown() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    run.play(TimelineSegment(9.0, blinks_per_minute=0.0))
    assert run.notifier.blink_nudge is None
    run.play(TimelineSegment(170.0, blinks_per_minute=LOW_RATE))
    assert run.notifier.count("show_blink_nudge") == 1
    run.play(TimelineSegment(15.0, blinks_per_minute=LOW_RATE))
    assert run.notifier.count("show_blink_nudge") == 2


def test_blink_nudge_mostly_incomplete_blinks_ask_for_full_closure() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE, blink=ScriptedBlink.INCOMPLETE))
    assert run.notifier.blink_nudge == SLOW_BLINK_MESSAGE


def test_blink_nudge_normal_blinking_never_shows() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(600.0))
    assert run.notifier.count("show_blink_nudge") == 0
