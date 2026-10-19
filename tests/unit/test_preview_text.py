from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.analysis.live_readout import LiveReading
from spare_my_eyes.ui.preview_text import describe_reading

READING = LiveReading(
    face_present=True,
    eye_openness=0.95,
    head_yaw_degrees=-31.4,
    looking_at_window=True,
    distance_cm=58.2,
    complete_blinks=12,
    incomplete_blinks=3,
)


def test_describe_reading_face_present_lists_every_measure() -> None:
    assert describe_reading(READING, WindowSide.LEFT) == [
        "Face: detected",
        "Eyes open: 95% of calibrated",
        "Blinks: 12 complete, 3 incomplete",
        "Distance: 58 cm",
        "Head turn: 31° left",
        "Looking at window (left): yes",
    ]


def test_describe_reading_positive_yaw_reports_right_turn() -> None:
    reading = LiveReading(True, 1.0, 27.0, False, 60.0, 0, 0)
    lines = describe_reading(reading, WindowSide.LEFT)
    assert "Head turn: 27° right" in lines
    assert "Looking at window (left): no" in lines


def test_describe_reading_small_yaw_reports_straight_ahead() -> None:
    reading = LiveReading(True, 1.0, 3.0, False, 60.0, 0, 0)
    assert "Head turn: straight ahead" in describe_reading(reading, WindowSide.RIGHT)


def test_describe_reading_without_face_keeps_only_presence_and_blinks() -> None:
    reading = LiveReading(False, 0.0, 0.0, False, None, 4, 1)
    assert describe_reading(reading, WindowSide.LEFT) == [
        "Face: not found",
        "Blinks: 4 complete, 1 incomplete",
    ]
