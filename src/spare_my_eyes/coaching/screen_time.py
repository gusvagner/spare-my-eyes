class ScreenTimeCounter:
    MAX_GAP_SECONDS = 2.0

    def __init__(self) -> None:
        self._seconds = 0.0
        self._last_present_at: float | None = None

    @property
    def seconds(self) -> float:
        return self._seconds

    def add_presence(self, now: float) -> None:
        if self._last_present_at is not None:
            gap = now - self._last_present_at
            self._seconds += min(max(gap, 0.0), self.MAX_GAP_SECONDS)
        self._last_present_at = now

    def pause(self) -> None:
        self._last_present_at = None

    def reset(self) -> None:
        self._seconds = 0.0
        self._last_present_at = None
