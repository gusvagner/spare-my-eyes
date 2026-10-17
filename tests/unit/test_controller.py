from dataclasses import dataclass, replace
from functools import partial

import pytest

from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.settings_store import InMemorySettingsStore
from tests.fakes.timeline import TimelineDriver
from tests.integration.pipeline_run import CALIBRATED_SETTINGS


@dataclass
class ControllerRig:
    controller: EyeCareController
    notifier: RecordingNotifier
    store: InMemorySettingsStore
    driver: TimelineDriver


def make_rig(settings: Settings, log_recorder: RecordingLogHandler) -> ControllerRig:
    clock = FakeClock()
    notifier = RecordingNotifier()
    store = InMemorySettingsStore(settings)
    factory = partial(
        build_coach, clock=clock, notifier=notifier, idle=FakeIdleTimeProvider(10_000.0)
    )
    controller = EyeCareController(settings, store, factory, notifier, clock, log_recorder.logger)
    driver = TimelineDriver(clock, controller.on_sample, controller.tick)
    return ControllerRig(controller, notifier, store, driver)


@pytest.fixture
def first_launch(log_recorder: RecordingLogHandler) -> ControllerRig:
    return make_rig(Settings(), log_recorder)


def test_init_uncalibrated_starts_calibration(first_launch: ControllerRig) -> None:
    assert first_launch.controller.is_calibrating
    assert first_launch.notifier.status is TrayStatus.CALIBRATING
    assert first_launch.notifier.calibration is not None


def test_on_sample_twenty_seconds_of_face_saves_calibration(
    first_launch: ControllerRig, log_recorder: RecordingLogHandler
) -> None:
    first_launch.driver.play(TimelineSegment(20.5))
    saved = first_launch.store.saved[-1]
    assert saved.open_ear_baseline == pytest.approx(0.30)
    assert saved.focal_scale == pytest.approx(660.0)
    assert not first_launch.controller.is_calibrating
    assert first_launch.notifier.calibration is None
    assert "calibration_completed" in log_recorder.events()


def test_on_sample_calibrated_start_goes_straight_to_coaching(
    log_recorder: RecordingLogHandler,
) -> None:
    rig = make_rig(CALIBRATED_SETTINGS, log_recorder)
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=4.8))
    assert rig.notifier.count("show_calibration") == 0
    assert rig.notifier.blink_nudge is not None


def test_on_camera_status_unavailable_cancels_and_active_restarts_calibration(
    first_launch: ControllerRig,
) -> None:
    first_launch.controller.on_camera_status(CameraStatus.UNAVAILABLE)
    assert not first_launch.controller.is_calibrating
    assert first_launch.notifier.calibration is None
    first_launch.controller.on_camera_status(CameraStatus.ACTIVE)
    assert first_launch.controller.is_calibrating


def test_recalibrate_hides_open_break_and_shows_calibration(
    log_recorder: RecordingLogHandler,
) -> None:
    rig = make_rig(replace(CALIBRATED_SETTINGS, break_interval_seconds=2.0), log_recorder)
    rig.driver.play(TimelineSegment(4.0))
    assert rig.notifier.break_progress is not None
    rig.controller.recalibrate()
    assert rig.notifier.break_progress is None
    assert rig.notifier.calibration is not None


def test_pause_for_during_calibration_cancels_it(first_launch: ControllerRig) -> None:
    first_launch.controller.pause_for(3600.0)
    assert not first_launch.controller.is_calibrating
    assert first_launch.controller.is_paused


def test_apply_settings_saves_and_rebuilds_coaching_with_new_values(
    log_recorder: RecordingLogHandler,
) -> None:
    rig = make_rig(CALIBRATED_SETTINGS, log_recorder)
    rig.controller.apply_settings(replace(CALIBRATED_SETTINGS, break_interval_seconds=2.0))
    assert rig.store.saved[-1].break_interval_seconds == 2.0
    rig.driver.play(TimelineSegment(4.0))
    assert rig.notifier.break_progress is not None
    assert "settings_applied" in log_recorder.events()


def test_apply_settings_keeps_known_camera_status(log_recorder: RecordingLogHandler) -> None:
    rig = make_rig(CALIBRATED_SETTINGS, log_recorder)
    rig.controller.on_camera_status(CameraStatus.UNAVAILABLE)
    rig.controller.apply_settings(CALIBRATED_SETTINGS)
    assert rig.notifier.status is TrayStatus.NO_CAMERA
