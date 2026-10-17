class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError(f"FakeClock cannot move backwards by {seconds} s; expected >= 0")
        self._now += seconds

    def set(self, timestamp: float) -> None:
        if timestamp < self._now:
            raise ValueError(
                f"FakeClock cannot move back to {timestamp}; expected >= current {self._now}"
            )
        self._now = timestamp
