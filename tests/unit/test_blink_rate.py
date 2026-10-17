import pytest

from spare_my_eyes.analysis.blink_detector import BlinkKind
from spare_my_eyes.analysis.blink_rate import BlinkRateMonitor
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import blink_of, samples_from_ears

FPS = 20.0


def present_from(monitor: BlinkRateMonitor, start: float, end: float) -> None:
    count = round((end - start) * FPS) + 1
    for sample in samples_from_ears([0.3] * count, fps=FPS, start=start):
        monitor.observe(sample)


def record_many(monitor: BlinkRateMonitor, kind: BlinkKind, count: int) -> None:
    for _ in range(count):
        monitor.record(blink_of(kind))


def test_stats_before_any_presence_returns_none() -> None:
    assert BlinkRateMonitor().stats() is None


def test_stats_ten_blinks_over_full_window_reports_five_per_minute() -> None:
    monitor = BlinkRateMonitor(window_seconds=120.0)
    for index in range(10):
        present_from(monitor, index * 12.0, index * 12.0 + 11.95)
        monitor.record(blink_of(BlinkKind.COMPLETE))
    present_from(monitor, 120.0, 120.0)
    stats = monitor.stats()
    assert stats is not None
    assert stats.blinks_per_minute == pytest.approx(5.0, abs=0.05)
    assert stats.window_full


def test_stats_partial_window_reports_rate_over_covered_time() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 30.0)
    record_many(monitor, BlinkKind.COMPLETE, 3)
    stats = monitor.stats()
    assert stats is not None
    assert stats.blinks_per_minute == pytest.approx(6.0)
    assert stats.covered_seconds == pytest.approx(30.0)
    assert not stats.window_full


def test_stats_blinks_older_than_window_are_dropped() -> None:
    monitor = BlinkRateMonitor(window_seconds=120.0)
    present_from(monitor, 0.0, 10.0)
    record_many(monitor, BlinkKind.COMPLETE, 6)
    present_from(monitor, 10.05, 140.0)
    stats = monitor.stats()
    assert stats is not None
    assert stats.blinks_per_minute == pytest.approx(0.0)


def test_observe_absence_does_not_advance_window() -> None:
    monitor = BlinkRateMonitor(window_seconds=120.0)
    present_from(monitor, 0.0, 60.0)
    record_many(monitor, BlinkKind.COMPLETE, 4)
    for step in range(1, 100):
        monitor.observe(FaceSample.absent(60.0 + step * 3.0))
    present_from(monitor, 400.0, 460.0)
    stats = monitor.stats()
    assert stats is not None
    assert stats.window_full
    assert stats.blinks_per_minute == pytest.approx(2.0)


def test_stats_incomplete_blinks_report_their_ratio() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 120.0)
    record_many(monitor, BlinkKind.COMPLETE, 3)
    record_many(monitor, BlinkKind.INCOMPLETE, 1)
    stats = monitor.stats()
    assert stats is not None
    assert stats.incomplete_ratio == pytest.approx(0.25)


def test_record_deliberate_closure_is_ignored() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 120.0)
    record_many(monitor, BlinkKind.DELIBERATE, 5)
    stats = monitor.stats()
    assert stats is not None
    assert stats.blinks_per_minute == pytest.approx(0.0)


def test_observe_long_gap_between_samples_counts_at_most_one_second() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 0.0)
    present_from(monitor, 3600.0, 3600.0)
    stats = monitor.stats()
    assert stats is not None
    assert stats.covered_seconds == pytest.approx(1.0)


def test_reset_clears_presence_and_blinks() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 30.0)
    record_many(monitor, BlinkKind.COMPLETE, 3)
    monitor.reset()
    assert monitor.stats() is None
