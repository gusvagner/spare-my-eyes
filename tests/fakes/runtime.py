from collections.abc import Callable


class FakeMainLoop:
    def __init__(self) -> None:
        self.scheduled: list[tuple[int, Callable[[], None]]] = []
        self.running = False
        self.stopped = False

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> None:
        self.scheduled.append((delay_ms, callback))

    def run(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.stopped = True


class FakeCaptureWorker:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.resumes = 0
        self._suspended = False

    @property
    def is_suspended(self) -> bool:
        return self._suspended

    def start(self) -> None:
        self.started = True

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self.stopped = True

    def suspend(self) -> None:
        self._suspended = True

    def resume(self) -> None:
        self._suspended = False
        self.resumes += 1


class RecordingCallback:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


class FailingCallback:
    def __call__(self) -> None:
        raise OSError("Settings window could not be created: no display available")
