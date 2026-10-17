import json
import logging
from pathlib import Path

from spare_my_eyes.structured_log import JsonLogFormatter, configure_file_logging, log_event
from tests.fakes.logs import RecordingLogHandler


def test_format_event_with_fields_produces_json_line(log_recorder: RecordingLogHandler) -> None:
    log_event(log_recorder.logger, logging.WARNING, "settings_file_corrupt", path="C:/x.json")
    entry = json.loads(JsonLogFormatter().format(log_recorder.records[0]))
    assert entry["event"] == "settings_file_corrupt"
    assert entry["level"] == "WARNING"
    assert entry["path"] == "C:/x.json"
    assert "time" in entry


def test_format_exception_includes_traceback(log_recorder: RecordingLogHandler) -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        log_recorder.logger.exception("capture_thread_crashed")
    entry = json.loads(JsonLogFormatter().format(log_recorder.records[0]))
    assert "RuntimeError: boom" in entry["exception"]


def test_configure_file_logging_writes_json_lines_to_log_dir(tmp_path: Path) -> None:
    logger = configure_file_logging(tmp_path / "logs", logger_name="tests.configure_file_logging")
    log_event(logger, logging.INFO, "app_started", scripted_camera=None)
    for handler in logger.handlers:
        handler.close()
    line = (tmp_path / "logs" / "spare-my-eyes.log").read_text(encoding="utf-8").splitlines()[0]
    assert json.loads(line)["event"] == "app_started"
