import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE_NAME = "spare-my-eyes.log"


def log_event(logger: logging.Logger, level: int, event: str, **fields: object) -> None:
    logger.log(level, event, extra={"fields": fields})


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            entry.update(fields)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_file_logging(log_dir: Path, logger_name: str = "spare_my_eyes") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger
