from dataclasses import dataclass, replace

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.settings import Settings

CLEAR_DISTANCE_MARGIN_CM = 5.0


@dataclass(frozen=True, slots=True)
class FieldRange:
    label: str
    minimum: int
    maximum: int


BREAK_INTERVAL_MINUTES = FieldRange("Break every (minutes)", 5, 120)
BLINK_THRESHOLD = FieldRange("Blink alert below (blinks/min)", 3, 20)
TOO_CLOSE_CM = FieldRange("Too close below (cm)", 30, 80)
CAMERA_INDEX = FieldRange("Camera number", 0, 9)


@dataclass(frozen=True, slots=True)
class SettingsFormInput:
    window_side: str
    break_interval_minutes: str
    blink_threshold: str
    too_close_cm: str
    camera_index: str
    start_with_windows: bool


@dataclass(frozen=True, slots=True)
class SettingsFormValues:
    window_side: WindowSide
    break_interval_minutes: int
    blink_threshold: int
    too_close_cm: int
    camera_index: int
    start_with_windows: bool


class SettingsFormError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def form_input_from(settings: Settings, start_with_windows: bool) -> SettingsFormInput:
    return SettingsFormInput(
        window_side=settings.window_side.value,
        break_interval_minutes=f"{settings.break_interval_seconds / 60:.0f}",
        blink_threshold=f"{settings.blink_rate_threshold_per_minute:.0f}",
        too_close_cm=f"{settings.too_close_cm:.0f}",
        camera_index=str(settings.camera_index),
        start_with_windows=start_with_windows,
    )


def parse_form(form: SettingsFormInput) -> SettingsFormValues:
    problems: list[str] = []
    values = SettingsFormValues(
        window_side=_window_side(form.window_side, problems),
        break_interval_minutes=_whole_number(
            form.break_interval_minutes, BREAK_INTERVAL_MINUTES, problems
        ),
        blink_threshold=_whole_number(form.blink_threshold, BLINK_THRESHOLD, problems),
        too_close_cm=_whole_number(form.too_close_cm, TOO_CLOSE_CM, problems),
        camera_index=_whole_number(form.camera_index, CAMERA_INDEX, problems),
        start_with_windows=form.start_with_windows,
    )
    if problems:
        raise SettingsFormError(problems)
    return values


def apply_form(settings: Settings, values: SettingsFormValues) -> Settings:
    return replace(
        settings,
        window_side=values.window_side,
        break_interval_seconds=values.break_interval_minutes * 60.0,
        blink_rate_threshold_per_minute=float(values.blink_threshold),
        too_close_cm=float(values.too_close_cm),
        distance_clear_cm=values.too_close_cm + CLEAR_DISTANCE_MARGIN_CM,
        camera_index=values.camera_index,
    )


def _whole_number(text: str, field: FieldRange, problems: list[str]) -> int:
    stripped = text.strip()
    if stripped.isdigit() and field.minimum <= int(stripped) <= field.maximum:
        return int(stripped)
    problems.append(
        f"{field.label} must be a whole number from {field.minimum} to {field.maximum}, "
        f"got {text!r}"
    )
    return field.minimum


def _window_side(text: str, problems: list[str]) -> WindowSide:
    if text in {side.value for side in WindowSide}:
        return WindowSide(text)
    problems.append(f"Window side must be 'left' or 'right', got {text!r}")
    return WindowSide.LEFT
