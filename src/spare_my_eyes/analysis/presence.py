from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PresenceUpdate:
    present: bool
    returned_after_seconds: float | None


class PresenceTracker:
    def __init__(self, absent_after_seconds: float = 60.0) -> None:
        self._absent_after = absent_after_seconds
        self._last_seen: float | None = None

    def update(self, now: float, seen_at: float | None) -> PresenceUpdate:
        previous = self._last_seen
        was_present = self._seen_recently(previous, now)
        self._last_seen = _latest(previous, seen_at)
        present = self._seen_recently(self._last_seen, now)
        return PresenceUpdate(present, self._absence(previous, was_present, present))

    def _absence(self, previous: float | None, was_present: bool, present: bool) -> float | None:
        if was_present or not present or previous is None or self._last_seen is None:
            return None
        return self._last_seen - previous

    def _seen_recently(self, seen_at: float | None, now: float) -> bool:
        return seen_at is not None and now - seen_at < self._absent_after


def _latest(current: float | None, candidate: float | None) -> float | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return max(current, candidate)
