import pytest

from spare_my_eyes.coaching.screen_time import ScreenTimeCounter


def add_every_second(counter: ScreenTimeCounter, start: int, end: int) -> None:
    for second in range(start, end + 1):
        counter.add_presence(float(second))


def test_add_presence_every_second_accumulates_elapsed_time() -> None:
    counter = ScreenTimeCounter()
    add_every_second(counter, 0, 10)
    assert counter.seconds == pytest.approx(10.0)


def test_pause_gap_after_pause_is_not_counted() -> None:
    counter = ScreenTimeCounter()
    add_every_second(counter, 0, 10)
    counter.pause()
    add_every_second(counter, 100, 105)
    assert counter.seconds == pytest.approx(15.0)


def test_add_presence_long_gap_counts_at_most_two_seconds() -> None:
    counter = ScreenTimeCounter()
    counter.add_presence(0.0)
    counter.add_presence(3600.0)
    assert counter.seconds == pytest.approx(2.0)


def test_reset_clears_accumulated_time() -> None:
    counter = ScreenTimeCounter()
    add_every_second(counter, 0, 10)
    counter.reset()
    counter.add_presence(11.0)
    assert counter.seconds == 0.0
