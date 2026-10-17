from spare_my_eyes.capture.scripted import ScriptedBlink, TimelineSegment

SCENARIOS: dict[str, tuple[TimelineSegment, ...]] = {
    "normal": (TimelineSegment(60.0),),
    "low-blink-rate": (TimelineSegment(180.0, blinks_per_minute=4.8),),
    "incomplete-blinks": (
        TimelineSegment(180.0, blinks_per_minute=4.8, blink=ScriptedBlink.INCOMPLETE),
    ),
    "too-close": (TimelineSegment(60.0, iris_diameter_px=15.0),),
    "away": (TimelineSegment(30.0), TimelineSegment(90.0, face_present=False)),
}
