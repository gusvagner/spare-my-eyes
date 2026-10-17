import time
from collections.abc import Callable

POLL_SECONDS = 0.01


def wait_until(condition: Callable[[], bool], timeout_seconds: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(POLL_SECONDS)
    return condition()
