import json
import logging
import os
from pathlib import Path
from typing import Protocol

from spare_my_eyes.settings import Settings, settings_from_overrides, settings_to_overrides
from spare_my_eyes.structured_log import log_event

_MAX_LOGGED_CONTENT = 2000


class SettingsStore(Protocol):
    def load(self) -> Settings: ...

    def save(self, settings: Settings) -> None: ...


class JsonSettingsStore:
    def __init__(self, path: Path, logger: logging.Logger) -> None:
        self._path = path
        self._logger = logger

    def load(self) -> Settings:
        if not self._path.exists():
            return Settings()
        text = self._path.read_text(encoding="utf-8", errors="replace")
        overrides = self._parse(text)
        if overrides is None:
            return Settings()
        return settings_from_overrides(overrides, self._logger)

    def save(self, settings: Settings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".json.tmp")
        content = json.dumps(settings_to_overrides(settings), indent=2) + "\n"
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, self._path)

    def ensure_file(self) -> Path:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text("{}\n", encoding="utf-8")
        return self._path

    def _parse(self, text: str) -> dict[str, object] | None:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
        log_event(
            self._logger,
            logging.WARNING,
            "settings_file_corrupt",
            path=str(self._path),
            content=text[:_MAX_LOGGED_CONTENT],
        )
        return None
