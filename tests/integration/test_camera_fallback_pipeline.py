from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.notifier import TrayStatus
from tests.integration.pipeline_run import PipelineRun


def test_camera_unavailable_reports_no_camera_and_keeps_time_based_breaks() -> None:
    run = PipelineRun()
    run.idle.seconds = 0.0
    run.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    assert run.notifier.status is TrayStatus.NO_CAMERA
    run.pass_time(1202)
    progress = run.notifier.break_progress
    assert progress is not None and not progress.verified
    run.idle.seconds = 10.0
    run.pass_time(32)
    assert run.notifier.break_progress is None


def test_camera_busy_pauses_measurement_and_keeps_time_based_breaks() -> None:
    run = PipelineRun()
    run.idle.seconds = 0.0
    run.coach.on_camera_status(CameraStatus.BUSY)
    run.pass_time(1202)
    assert run.notifier.status is TrayStatus.PAUSED
    progress = run.notifier.break_progress
    assert progress is not None and not progress.verified


def test_camera_unplugged_hides_visible_blink_nudge() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(121.0, blinks_per_minute=4.8))
    assert run.notifier.blink_nudge is not None
    run.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    assert run.notifier.blink_nudge is None


def test_camera_back_reports_monitoring() -> None:
    run = PipelineRun()
    run.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    run.coach.on_camera_status(CameraStatus.ACTIVE)
    assert run.notifier.status is TrayStatus.MONITORING
