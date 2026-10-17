import queue

import pytest

from spare_my_eyes.capture.camera_errors import CameraBusyError, CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus, FaceSampleSource
from spare_my_eyes.capture.worker import CameraStatusChanged, CaptureMessage, CaptureWorker
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.sample_sources import (
    CrashOnceSampleSource,
    FailingSampleSource,
    SteadySampleSource,
)
from tests.fakes.waiting import wait_until

RETRY_SECONDS = 0.05


@pytest.fixture
def outbox() -> queue.Queue[CaptureMessage]:
    return queue.Queue()


def make_worker(
    source: FaceSampleSource, outbox: queue.Queue[CaptureMessage], log: RecordingLogHandler
) -> CaptureWorker:
    return CaptureWorker(source, outbox, RETRY_SECONDS, log.logger, restart_delay_seconds=0.01)


def test_start_working_camera_reports_active_then_samples(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    worker = make_worker(SteadySampleSource(), outbox, log_recorder)
    worker.start()
    try:
        first, second = outbox.get(timeout=2), outbox.get(timeout=2)
    finally:
        worker.stop()
    assert first == CameraStatusChanged(CameraStatus.ACTIVE)
    assert isinstance(second, FaceSample)


def test_start_missing_camera_reports_unavailable_and_retries(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    source = FailingSampleSource(CameraUnavailableError("no camera at index 0"))
    worker = make_worker(source, outbox, log_recorder)
    worker.start()
    try:
        assert wait_until(lambda: source.open_calls >= 2)
    finally:
        worker.stop()
    assert outbox.get(timeout=1) == CameraStatusChanged(CameraStatus.UNAVAILABLE)
    assert log_recorder.fields_of("camera_failed")["status"] == "unavailable"


def test_start_busy_camera_reports_busy(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    worker = make_worker(FailingSampleSource(CameraBusyError("in use")), outbox, log_recorder)
    worker.start()
    try:
        message = outbox.get(timeout=2)
    finally:
        worker.stop()
    assert message == CameraStatusChanged(CameraStatus.BUSY)


def test_start_unexpected_error_logs_and_restarts(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    worker = make_worker(CrashOnceSampleSource(), outbox, log_recorder)
    worker.start()
    try:
        message = outbox.get(timeout=2)
    finally:
        worker.stop()
    assert message == CameraStatusChanged(CameraStatus.ACTIVE)
    assert "capture_thread_crashed" in log_recorder.events()


def test_suspend_releases_camera_and_resume_reopens_it(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    source = SteadySampleSource()
    worker = make_worker(source, outbox, log_recorder)
    worker.start()
    try:
        assert wait_until(lambda: source.open_calls == 1)
        worker.suspend()
        assert wait_until(lambda: source.close_calls >= 1)
        worker.resume()
        assert wait_until(lambda: source.open_calls == 2)
    finally:
        worker.stop()


def test_stop_running_worker_ends_thread(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    worker = make_worker(SteadySampleSource(), outbox, log_recorder)
    worker.start()
    worker.stop()
    assert not worker.is_running
