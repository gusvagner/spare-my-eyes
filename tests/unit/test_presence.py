from spare_my_eyes.analysis.presence import PresenceTracker, PresenceUpdate


def test_update_first_sighting_is_present_without_return() -> None:
    assert PresenceTracker().update(0.0, 0.0) == PresenceUpdate(True, None)


def test_update_never_seen_is_absent() -> None:
    assert PresenceTracker().update(10.0, None) == PresenceUpdate(False, None)


def test_update_short_gap_stays_present() -> None:
    tracker = PresenceTracker(absent_after_seconds=60.0)
    tracker.update(0.0, 0.0)
    assert tracker.update(59.0, None) == PresenceUpdate(True, None)


def test_update_no_sighting_for_absent_after_is_absent() -> None:
    tracker = PresenceTracker(absent_after_seconds=60.0)
    tracker.update(0.0, 0.0)
    assert tracker.update(60.0, None) == PresenceUpdate(False, None)


def test_update_return_after_absence_reports_absence_duration() -> None:
    tracker = PresenceTracker()
    tracker.update(0.0, 0.0)
    tracker.update(100.0, None)
    assert tracker.update(400.0, 400.0) == PresenceUpdate(True, 400.0)


def test_update_sighting_after_long_silent_gap_reports_absence() -> None:
    tracker = PresenceTracker()
    tracker.update(0.0, 0.0)
    assert tracker.update(3600.0, 3600.0) == PresenceUpdate(True, 3600.0)


def test_update_older_sighting_does_not_move_last_seen_back() -> None:
    tracker = PresenceTracker()
    tracker.update(10.0, 10.0)
    tracker.update(20.0, 5.0)
    assert tracker.update(69.0, None).present


def test_update_stale_sighting_while_absent_does_not_report_return() -> None:
    tracker = PresenceTracker()
    tracker.update(0.0, 0.0)
    assert tracker.update(500.0, 100.0) == PresenceUpdate(False, None)
