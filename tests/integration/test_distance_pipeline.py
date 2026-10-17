from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.distance_alert import MOVE_BACK_MESSAGE
from tests.integration.pipeline_run import CALIBRATED_SETTINGS, PipelineRun


def at_cm(duration: float, centimeters: float) -> TimelineSegment:
    assert CALIBRATED_SETTINGS.focal_scale is not None
    return TimelineSegment(duration, iris_diameter_px=CALIBRATED_SETTINGS.focal_scale / centimeters)


def test_distance_alert_shows_after_thirty_seconds_close_and_hides_past_55_cm() -> None:
    run = PipelineRun()
    run.play(at_cm(29.0, 45.0))
    assert run.notifier.distance_alert is None
    run.play(at_cm(2.0, 45.0))
    assert run.notifier.distance_alert == MOVE_BACK_MESSAGE
    run.play(at_cm(10.0, 52.0))
    assert run.notifier.distance_alert == MOVE_BACK_MESSAGE
    run.play(at_cm(5.0, 58.0))
    assert run.notifier.distance_alert is None


def test_distance_alert_respects_five_minute_cooldown() -> None:
    run = PipelineRun()
    run.play(at_cm(31.0, 45.0))
    run.play(at_cm(5.0, 58.0))
    run.play(at_cm(60.0, 45.0))
    assert run.notifier.distance_alert is None
    run.play(at_cm(250.0, 45.0))
    assert run.notifier.distance_alert == MOVE_BACK_MESSAGE
