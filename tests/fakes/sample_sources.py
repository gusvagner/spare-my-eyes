import time

from spare_my_eyes.capture.face_sample import FaceSample

SAMPLE_PACE_SECONDS = 0.005


class FailingSampleSource:
    def __init__(self, error: Exception) -> None:
        self._error = error
        self.open_calls = 0
        self.close_calls = 0

    def open(self) -> None:
        self.open_calls += 1
        raise self._error

    def next_sample(self) -> FaceSample:
        raise self._error

    def close(self) -> None:
        self.close_calls += 1


class SteadySampleSource:
    def __init__(self) -> None:
        self.open_calls = 0
        self.close_calls = 0

    def open(self) -> None:
        self.open_calls += 1

    def next_sample(self) -> FaceSample:
        time.sleep(SAMPLE_PACE_SECONDS)
        return FaceSample(timestamp=time.monotonic(), face_present=True)

    def close(self) -> None:
        self.close_calls += 1


class CrashOnceSampleSource(SteadySampleSource):
    def open(self) -> None:
        super().open()
        if self.open_calls == 1:
            raise RuntimeError("simulated crash on first open")
