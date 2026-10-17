from dataclasses import replace

import pytest

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.settings import Settings
from spare_my_eyes.settings_form import (
    SettingsFormError,
    SettingsFormInput,
    apply_form,
    form_input_from,
    parse_form,
)

DEFAULT_FORM = SettingsFormInput("left", "20", "8", "50", "0", False)


def test_form_input_from_defaults_shows_spec_values() -> None:
    assert form_input_from(Settings(), start_with_windows=False) == DEFAULT_FORM


def test_parse_form_valid_input_returns_values() -> None:
    values = parse_form(replace(DEFAULT_FORM, window_side="right", break_interval_minutes=" 30 "))
    assert values.window_side is WindowSide.RIGHT
    assert values.break_interval_minutes == 30


def test_parse_form_several_bad_fields_reports_all_problems() -> None:
    form = replace(DEFAULT_FORM, break_interval_minutes="abc", too_close_cm="200")
    with pytest.raises(SettingsFormError) as caught:
        parse_form(form)
    assert len(caught.value.problems) == 2
    assert "Break every (minutes)" in caught.value.problems[0]
    assert "from 30 to 80, got '200'" in caught.value.problems[1]


def test_parse_form_unknown_window_side_reports_problem() -> None:
    with pytest.raises(SettingsFormError, match="Window side"):
        parse_form(replace(DEFAULT_FORM, window_side="up"))


def test_apply_form_converts_units_and_keeps_calibration() -> None:
    calibrated = replace(Settings(), open_ear_baseline=0.3, focal_scale=660.0)
    form = replace(DEFAULT_FORM, break_interval_minutes="30", too_close_cm="45", camera_index="1")
    settings = apply_form(calibrated, parse_form(form))
    assert settings.break_interval_seconds == 1800.0
    assert settings.too_close_cm == 45.0
    assert settings.distance_clear_cm == 50.0
    assert settings.camera_index == 1
    assert settings.open_ear_baseline == 0.3


def test_apply_form_unchanged_defaults_round_trip_to_defaults() -> None:
    assert apply_form(Settings(), parse_form(DEFAULT_FORM)) == Settings()
