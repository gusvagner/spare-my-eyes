from spare_my_eyes.capture.scripted import ScriptedBlink, TimelineSegment
from spare_my_eyes.coaching.break_session import BreakStep
from spare_my_eyes.coaching.notifier import TrayStatus
from tests.integration.pipeline_run import PipelineRun

TWENTY_MINUTES = 1200.0


def run_until_break() -> PipelineRun:
    run = PipelineRun()
    run.play(TimelineSegment(TWENTY_MINUTES + 2.0))
    return run


def test_break_twenty_minutes_of_presence_shows_break_card() -> None:
    progress = run_until_break().notifier.break_progress
    assert progress is not None
    assert progress.step is BreakStep.LOOK_OUT
    assert progress.verified


def test_break_gaze_and_slow_blinks_complete_it_and_reset_screen_time() -> None:
    run = run_until_break()
    run.play(TimelineSegment(21.0, head_yaw_degrees=-30.0))
    progress = run.notifier.break_progress
    assert progress is not None and progress.step is BreakStep.SLOW_BLINKS
    run.play(TimelineSegment(10.5, blinks_per_minute=30.0, blink=ScriptedBlink.SLOW))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(1150.0))
    assert run.notifier.break_progress is None


def test_break_looking_to_the_wrong_side_does_not_progress() -> None:
    run = run_until_break()
    run.play(TimelineSegment(21.0, head_yaw_degrees=30.0))
    progress = run.notifier.break_progress
    assert progress is not None
    assert progress.gaze_seconds == 0.0


def test_break_snooze_brings_card_back_after_five_minutes() -> None:
    run = run_until_break()
    run.coach.snooze_break()
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(298.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(4.0))
    assert run.notifier.break_progress is not None


def test_break_skip_hides_card_and_resets_screen_time() -> None:
    run = run_until_break()
    run.coach.skip_break()
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(1150.0))
    assert run.notifier.break_progress is None


def test_break_two_minutes_without_interaction_times_out() -> None:
    run = run_until_break()
    run.play(TimelineSegment(123.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(1100.0))
    assert run.notifier.break_progress is None


def test_break_short_absence_pauses_screen_time() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(600.0))
    run.play(TimelineSegment(240.0, face_present=False))
    run.play(TimelineSegment(530.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(15.0))
    assert run.notifier.break_progress is not None


def test_break_absence_of_five_minutes_resets_screen_time() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(600.0))
    run.play(TimelineSegment(301.0, face_present=False))
    run.play(TimelineSegment(1190.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(15.0))
    assert run.notifier.break_progress is not None


def test_break_sleep_gap_resets_screen_time() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(600.0))
    run.clock.advance(3600.0)
    run.play(TimelineSegment(1190.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(15.0))
    assert run.notifier.break_progress is not None


def test_break_face_never_detected_but_user_typing_still_gets_unverified_break() -> None:
    run = PipelineRun()
    run.idle.seconds = 0.0
    run.play(TimelineSegment(TWENTY_MINUTES + 2.0, face_present=False))
    progress = run.notifier.break_progress
    assert progress is not None
    assert not progress.verified


def test_pause_hides_open_break_card() -> None:
    run = run_until_break()
    run.coach.pause_for(3600.0)
    assert run.notifier.break_progress is None
    assert run.notifier.status is TrayStatus.PAUSED
