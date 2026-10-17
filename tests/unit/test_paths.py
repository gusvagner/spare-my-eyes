from pathlib import Path

import pytest

from spare_my_eyes.paths import AppPaths, default_data_dir


def test_default_data_dir_appdata_set_returns_spare_my_eyes_folder() -> None:
    assert default_data_dir({"APPDATA": "C:/Users/me/AppData/Roaming"}) == Path(
        "C:/Users/me/AppData/Roaming/SpareMyEyes"
    )


def test_default_data_dir_appdata_missing_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="APPDATA"):
        default_data_dir({})


def test_app_paths_layout_puts_settings_and_logs_in_data_dir() -> None:
    paths = AppPaths(Path("D:/data"))
    assert paths.settings_file == Path("D:/data/settings.json")
    assert paths.log_dir == Path("D:/data/logs")
