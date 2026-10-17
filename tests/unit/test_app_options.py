from pathlib import Path

import pytest

from spare_my_eyes.app import parse_options

ENVIRONMENT = {"APPDATA": "C:/Users/me/AppData/Roaming"}


def test_parse_options_no_arguments_uses_appdata_and_real_camera() -> None:
    options = parse_options([], ENVIRONMENT)
    assert options.data_dir == Path("C:/Users/me/AppData/Roaming/SpareMyEyes")
    assert options.scripted_camera is None
    assert options.exit_after_seconds is None


def test_parse_options_all_flags_are_read() -> None:
    argv = ["--scripted-camera", "normal", "--exit-after", "6", "--data-dir", "D:/tmp"]
    options = parse_options(argv, ENVIRONMENT)
    assert options.scripted_camera == "normal"
    assert options.exit_after_seconds == 6.0
    assert options.data_dir == Path("D:/tmp")


def test_parse_options_unknown_scenario_exits_with_usage_error() -> None:
    with pytest.raises(SystemExit):
        parse_options(["--scripted-camera", "nonexistent"], ENVIRONMENT)
