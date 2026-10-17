from spare_my_eyes.analysis.distance import ARM_LENGTH_CM
from spare_my_eyes.capture.scripted import DEFAULT_IRIS_DIAMETER_PX, OPEN_EAR, TimelineSegment
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.timeline import TimelineDriver

CALIBRATED_SETTINGS = Settings(
    open_ear_baseline=OPEN_EAR, focal_scale=DEFAULT_IRIS_DIAMETER_PX * ARM_LENGTH_CM
)
USER_NOT_TYPING_SECONDS = 10_000.0


class PipelineRun:
    """The real analyzers and Coach, driven by a scripted timeline on a fake clock."""

    def __init__(self, settings: Settings = CALIBRATED_SETTINGS) -> None:
        self.clock = FakeClock()
        self.notifier = RecordingNotifier()
        self.idle = FakeIdleTimeProvider(USER_NOT_TYPING_SECONDS)
        self.coach = build_coach(settings, self.clock, self.notifier, self.idle)
        self._driver = TimelineDriver(self.clock, self.coach.on_sample, self.coach.tick)

    def play(self, *segments: TimelineSegment) -> None:
        self._driver.play(*segments)

    def pass_time(self, seconds: int) -> None:
        self._driver.pass_time(seconds)
