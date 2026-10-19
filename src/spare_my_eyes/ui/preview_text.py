from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.analysis.live_readout import LiveReading

STRAIGHT_AHEAD_DEGREES = 5.0
WAITING_FOR_CAMERA = (
    "No camera image yet. The app may be paused, or another app is using the camera."
)


def describe_reading(reading: LiveReading, window_side: WindowSide) -> list[str]:
    blinks = f"Blinks: {reading.complete_blinks} complete, {reading.incomplete_blinks} incomplete"
    if not reading.face_present:
        return ["Face: not found", blinks]
    looking = "yes" if reading.looking_at_window else "no"
    return [
        "Face: detected",
        f"Eyes open: {reading.eye_openness:.0%} of calibrated",
        blinks,
        _describe_distance(reading.distance_cm),
        _describe_head_turn(reading.head_yaw_degrees),
        f"Looking at window ({window_side.value}): {looking}",
    ]


def _describe_distance(distance_cm: float | None) -> str:
    if distance_cm is None:
        return "Distance: unknown"
    return f"Distance: {distance_cm:.0f} cm"


def _describe_head_turn(yaw_degrees: float) -> str:
    if abs(yaw_degrees) < STRAIGHT_AHEAD_DEGREES:
        return "Head turn: straight ahead"
    direction = "left" if yaw_degrees < 0 else "right"
    return f"Head turn: {abs(yaw_degrees):.0f}° {direction}"
