import json
from dataclasses import replace
from pathlib import Path

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.settings import Settings
from spare_my_eyes.settings_store import JsonSettingsStore
from tests.fakes.logs import RecordingLogHandler


def test_load_missing_file_returns_defaults(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    store = JsonSettingsStore(tmp_path / "settings.json", log_recorder.logger)
    assert store.load() == Settings()


def test_save_then_load_round_trips_and_writes_only_overrides(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path, log_recorder.logger)
    settings = replace(Settings(), window_side=WindowSide.RIGHT, focal_scale=660.0)
    store.save(settings)
    assert store.load() == settings
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "window_side": "right",
        "focal_scale": 660.0,
    }


def test_save_missing_parent_directory_creates_it(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "SpareMyEyes" / "settings.json"
    JsonSettingsStore(path, log_recorder.logger).save(Settings())
    assert path.is_file()


def test_load_invalid_json_logs_content_and_returns_defaults_without_overwriting(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert JsonSettingsStore(path, log_recorder.logger).load() == Settings()
    assert path.read_text(encoding="utf-8") == "{not json"
    assert log_recorder.fields_of("settings_file_corrupt")["content"] == "{not json"


def test_load_json_array_is_treated_as_corrupt(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    path.write_text("[1, 2]", encoding="utf-8")
    assert JsonSettingsStore(path, log_recorder.logger).load() == Settings()
    assert "settings_file_corrupt" in log_recorder.events()


def test_ensure_file_missing_creates_empty_overrides(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "SpareMyEyes" / "settings.json"
    assert JsonSettingsStore(path, log_recorder.logger).ensure_file() == path
    assert path.read_text(encoding="utf-8") == "{}\n"


def test_ensure_file_existing_file_is_left_untouched(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"window_side": "right"}', encoding="utf-8")
    JsonSettingsStore(path, log_recorder.logger).ensure_file()
    assert path.read_text(encoding="utf-8") == '{"window_side": "right"}'


def test_save_after_corrupt_load_backs_up_original_file(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"window_side": "right",}', encoding="utf-8")
    store = JsonSettingsStore(path, log_recorder.logger)
    store.save(replace(store.load(), focal_scale=660.0))
    backup = tmp_path / "settings.json.bak"
    assert backup.read_text(encoding="utf-8") == '{"window_side": "right",}'


def test_save_after_load_with_rejected_key_backs_up_original_file(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"window_sid": "right"}', encoding="utf-8")
    store = JsonSettingsStore(path, log_recorder.logger)
    store.save(store.load())
    assert (tmp_path / "settings.json.bak").is_file()


def test_save_after_clean_load_makes_no_backup(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"window_side": "right"}', encoding="utf-8")
    store = JsonSettingsStore(path, log_recorder.logger)
    store.save(store.load())
    assert not (tmp_path / "settings.json.bak").exists()
