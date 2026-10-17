from functools import partial

from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.blink_nudge import BLINK_MESSAGE
from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.settings_store import InMemorySettingsStore
from tests.fakes.timeline import TimelineDriver


def test_first_launch_calibrates_then_nudges_on_low_blink_rate(
    log_recorder: RecordingLogHandler,
) -> None:
    clock = FakeClock()
    notifier = RecordingNotifier()
    factory = partial(
        build_coach, clock=clock, notifier=notifier, idle=FakeIdleTimeProvider(10_000.0)
    )
    controller = EyeCareController(
        Settings(), InMemorySettingsStore(), factory, notifier, clock, log_recorder.logger
    )
    driver = TimelineDriver(clock, controller.on_sample, controller.tick)
    driver.play(TimelineSegment(21.0))
    assert controller.settings.is_calibrated
    driver.play(TimelineSegment(121.0, blinks_per_minute=4.8))
    assert notifier.blink_nudge == BLINK_MESSAGE
