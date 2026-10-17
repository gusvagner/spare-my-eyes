from dataclasses import replace

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.settings import Settings, settings_from_overrides, settings_to_overrides
from tests.fakes.logs import RecordingLogHandler


def test_settings_defaults_match_spec() -> None:
    settings = Settings()
    assert settings.window_side is WindowSide.LEFT
    assert settings.frames_per_second == 20.0
    assert settings.blink_rate_threshold_per_minute == 8.0
    assert settings.too_close_cm == 50.0
    assert settings.break_interval_seconds == 1200.0
    assert not settings.is_calibrated


def test_settings_from_overrides_valid_values_replace_defaults(
    log_recorder: RecordingLogHandler,
) -> None:
    overrides = {"window_side": "right", "break_interval_seconds": 600, "break_slow_blinks": 3}
    settings = settings_from_overrides(overrides, log_recorder.logger)
    assert settings.window_side is WindowSide.RIGHT
    assert settings.break_interval_seconds == 600.0
    assert settings.break_slow_blinks == 3
    assert log_recorder.records == []


def test_settings_from_overrides_unknown_key_is_logged_and_ignored(
    log_recorder: RecordingLogHandler,
) -> None:
    settings = settings_from_overrides({"brightness": 3}, log_recorder.logger)
    assert settings == Settings()
    assert log_recorder.fields_of("settings_unknown_key") == {"key": "brightness"}


def test_settings_from_overrides_wrong_type_keeps_default_and_logs(
    log_recorder: RecordingLogHandler,
) -> None:
    overrides = {"frames_per_second": "fast", "snooze_seconds": 120}
    settings = settings_from_overrides(overrides, log_recorder.logger)
    assert settings.frames_per_second == 20.0
    assert settings.snooze_seconds == 120.0
    fields = log_recorder.fields_of("settings_invalid_value")
    assert fields["key"] == "frames_per_second"
    assert fields["value"] == "'fast'"


def test_settings_from_overrides_negative_number_keeps_default(
    log_recorder: RecordingLogHandler,
) -> None:
    assert settings_from_overrides({"too_close_cm": -5}, log_recorder.logger).too_close_cm == 50.0


def test_settings_from_overrides_boolean_for_number_keeps_default(
    log_recorder: RecordingLogHandler,
) -> None:
    settings = settings_from_overrides({"snooze_seconds": True}, log_recorder.logger)
    assert settings.snooze_seconds == 300.0


def test_settings_from_overrides_invalid_window_side_keeps_default(
    log_recorder: RecordingLogHandler,
) -> None:
    settings = settings_from_overrides({"window_side": "up"}, log_recorder.logger)
    assert settings.window_side is WindowSide.LEFT


def test_settings_to_overrides_defaults_returns_empty_dict() -> None:
    assert settings_to_overrides(Settings()) == {}


def test_settings_to_overrides_changed_values_returns_only_changes() -> None:
    settings = replace(Settings(), window_side=WindowSide.RIGHT, open_ear_baseline=0.3)
    assert settings_to_overrides(settings) == {"window_side": "right", "open_ear_baseline": 0.3}


def test_is_calibrated_both_values_set_returns_true() -> None:
    assert replace(Settings(), open_ear_baseline=0.3, focal_scale=660.0).is_calibrated
