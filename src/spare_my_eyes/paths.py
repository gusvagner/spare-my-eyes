from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_FOLDER_NAME = "SpareMyEyes"


@dataclass(frozen=True, slots=True)
class AppPaths:
    data_dir: Path

    @property
    def settings_file(self) -> Path:
        return self.data_dir / "settings.json"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"


def default_data_dir(environment: Mapping[str, str]) -> Path:
    appdata = environment.get("APPDATA")
    if not appdata:
        raise RuntimeError(
            f"APPDATA is not set (got {appdata!r}); expected a Windows profile path such as "
            r"C:\Users\me\AppData\Roaming"
        )
    return Path(appdata) / APP_FOLDER_NAME
