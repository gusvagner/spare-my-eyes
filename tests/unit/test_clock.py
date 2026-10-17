from spare_my_eyes.clock import MonotonicClock


def test_now_called_twice_never_goes_backwards() -> None:
    clock = MonotonicClock()
    first = clock.now()
    assert clock.now() >= first
