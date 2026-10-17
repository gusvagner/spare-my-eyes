import math


class Cooldown:
    def __init__(self, seconds: float) -> None:
        self._seconds = seconds
        self._ready_at = -math.inf

    def is_ready(self, now: float) -> bool:
        return now >= self._ready_at

    def start(self, now: float) -> None:
        self._ready_at = now + self._seconds

    def clear(self) -> None:
        self._ready_at = -math.inf
