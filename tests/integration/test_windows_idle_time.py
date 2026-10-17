from spare_my_eyes.system.idle_time import WindowsIdleTimeProvider


def test_idle_seconds_real_windows_session_returns_non_negative_seconds() -> None:
    assert 0.0 <= WindowsIdleTimeProvider().idle_seconds() < 50 * 24 * 3600
