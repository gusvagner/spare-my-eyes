import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, replace
from typing import Any

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.structured_log import log_event


@dataclass(frozen=True, slots=True)
class Settings:
    window_side: WindowSide = WindowSide.LEFT
    camera_index: int = 0
    frames_per_second: float = 20.0
    blink_rate_threshold_per_minute: float = 8.0
    incomplete_ratio_threshold: float = 0.3
    blink_window_seconds: float = 120.0
    nudge_max_seconds: float = 8.0
    nudge_cooldown_seconds: float = 180.0
    nudge_hide_after_complete_blinks: int = 2
    too_close_cm: float = 50.0
    distance_clear_cm: float = 55.0
    distance_hold_seconds: float = 30.0
    distance_cooldown_seconds: float = 300.0
    break_interval_seconds: float = 1200.0
    break_gaze_seconds: float = 20.0
    break_min_yaw_degrees: float = 25.0
    break_slow_blinks: int = 5
    slow_blink_min_seconds: float = 0.3
    break_inactivity_timeout_seconds: float = 120.0
    snooze_seconds: float = 300.0
    absent_after_seconds: float = 60.0
    absence_reset_seconds: float = 300.0
    camera_retry_seconds: float = 60.0
    open_ear_baseline: float | None = None
    focal_scale: float | None = None

    @property
    def is_calibrated(self) -> bool:
        return self.open_ear_baseline is not None and self.focal_scale is not None


def settings_from_overrides(overrides: Mapping[str, object], logger: logging.Logger) -> Settings:
    accepted: dict[str, Any] = {}
    for key, value in overrides.items():
        parsed = _parse_override(key, value, logger)
        if parsed is not None:
            accepted[key] = parsed
    return replace(Settings(), **accepted)


def settings_to_overrides(settings: Settings) -> dict[str, object]:
    defaults = Settings()
    return {
        field.name: getattr(settings, field.name)
        for field in fields(Settings)
        if getattr(settings, field.name) != getattr(defaults, field.name)
    }


def _parse_override(key: str, value: object, logger: logging.Logger) -> object | None:
    parser = _PARSERS.get(key)
    if parser is None:
        log_event(logger, logging.WARNING, "settings_unknown_key", key=key)
        return None
    try:
        return parser(value)
    except ValueError as error:
        log_event(
            logger,
            logging.WARNING,
            "settings_invalid_value",
            key=key,
            value=repr(value),
            reason=str(error),
        )
        return None


def _positive_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise ValueError(f"expected a positive number, got {value!r}")
    return float(value)


def _optional_positive_float(value: object) -> float | None:
    return None if value is None else _positive_float(value)


def _positive_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"expected a positive integer, got {value!r}")
    return value


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"expected an integer >= 0, got {value!r}")
    return value


def _window_side(value: object) -> WindowSide:
    if not isinstance(value, str) or value not in {side.value for side in WindowSide}:
        raise ValueError(f"expected 'left' or 'right', got {value!r}")
    return WindowSide(value)


_FLOAT_FIELDS = (
    "frames_per_second",
    "blink_rate_threshold_per_minute",
    "incomplete_ratio_threshold",
    "blink_window_seconds",
    "nudge_max_seconds",
    "nudge_cooldown_seconds",
    "too_close_cm",
    "distance_clear_cm",
    "distance_hold_seconds",
    "distance_cooldown_seconds",
    "break_interval_seconds",
    "break_gaze_seconds",
    "break_min_yaw_degrees",
    "slow_blink_min_seconds",
    "break_inactivity_timeout_seconds",
    "snooze_seconds",
    "absent_after_seconds",
    "absence_reset_seconds",
    "camera_retry_seconds",
)

_PARSERS: dict[str, Callable[[object], object]] = {
    "window_side": _window_side,
    "camera_index": _non_negative_int,
    "nudge_hide_after_complete_blinks": _positive_int,
    "break_slow_blinks": _positive_int,
    "open_ear_baseline": _optional_positive_float,
    "focal_scale": _optional_positive_float,
    **{name: _positive_float for name in _FLOAT_FIELDS},
}
