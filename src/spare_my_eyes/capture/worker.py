import logging
import queue
import threading
from dataclasses import dataclass

from spare_my_eyes.capture.camera_errors import CameraBusyError, CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus, FaceSampleSource
from spare_my_eyes.structured_log import log_event


@dataclass(frozen=True, slots=True)
class CameraStatusChanged:
    status: CameraStatus


CaptureMessage = FaceSample | CameraStatusChanged


class CaptureWorker:
    """Reads face samples on a background thread and posts them to the main thread's queue."""

    SUSPENDED_POLL_SECONDS = 0.5

    def __init__(
        self,
        source: FaceSampleSource,
        outbox: queue.Queue[CaptureMessage],
        retry_seconds: float,
        logger: logging.Logger,
        restart_delay_seconds: float = 1.0,
    ) -> None:
        self._source = source
        self._outbox = outbox
        self._retry_seconds = retry_seconds
        self._logger = logger
        self._restart_delay = restart_delay_seconds
        self._stopping = threading.Event()
        self._suspended = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_suspended(self) -> bool:
        return self._suspended.is_set()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="capture", daemon=True)
        self._thread.start()

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(timeout_seconds)

    def suspend(self) -> None:
        self._suspended.set()

    def resume(self) -> None:
        self._suspended.clear()

    def _run(self) -> None:
        while not self._stopping.is_set():
            if self._suspended.is_set():
                self._stopping.wait(self.SUSPENDED_POLL_SECONDS)
                continue
            self._run_capture_session()

    def _run_capture_session(self) -> None:
        try:
            self._capture_until_interrupted()
        except CameraUnavailableError as error:
            self._wait_after_failure(CameraStatus.UNAVAILABLE, error)
        except CameraBusyError as error:
            self._wait_after_failure(CameraStatus.BUSY, error)
        except Exception:
            self._logger.exception("capture_thread_crashed")
            self._stopping.wait(self._restart_delay)
        finally:
            self._source.close()

    def _capture_until_interrupted(self) -> None:
        self._source.open()
        self._outbox.put(CameraStatusChanged(CameraStatus.ACTIVE))
        while not self._stopping.is_set() and not self._suspended.is_set():
            self._outbox.put(self._source.next_sample())

    def _wait_after_failure(self, status: CameraStatus, error: Exception) -> None:
        log_event(
            self._logger, logging.WARNING, "camera_failed", status=status.value, reason=str(error)
        )
        self._outbox.put(CameraStatusChanged(status))
        self._stopping.wait(self._retry_seconds)
