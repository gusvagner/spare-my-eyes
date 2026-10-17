import logging
from typing import Self


class RecordingLogHandler(logging.Handler):
    def __init__(self, logger: logging.Logger) -> None:
        super().__init__(level=logging.DEBUG)
        self.logger = logger
        self.records: list[logging.LogRecord] = []

    @classmethod
    def attached_to_new_logger(cls, name: str) -> Self:
        logger = logging.getLogger(f"tests.{name}")
        logger.handlers.clear()
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        handler = cls(logger)
        logger.addHandler(handler)
        return handler

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def events(self) -> list[str]:
        return [record.getMessage() for record in self.records]

    def fields_of(self, event: str) -> dict[str, object]:
        for record in self.records:
            if record.getMessage() == event:
                fields = getattr(record, "fields", {})
                return dict(fields) if isinstance(fields, dict) else {}
        raise AssertionError(f"No log record with event {event!r}; recorded {self.events()!r}")
