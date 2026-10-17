import queue
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

import pytest

from spare_my_eyes.app_runtime import AppRuntime, RuntimeChannels, UserCommand
from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.capture.worker import CameraStatusChanged
from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.coaching.notifier import TrayStatus
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.runtime import (
    FailingCallback,
    FakeCaptureWorker,
    FakeMainLoop,
    RecordingCallback,
)
from tests.fakes.settings_store import InMemorySettingsStore
from tests.fakes.tray import FakeTray
from tests.integration.pipeline_run import CALIBRATED_SETTINGS


@dataclass
class RuntimeRig:
    runtime: AppRuntime
    loop: FakeMainLoop
    worker: FakeCaptureWorker
    tray: FakeTray
    channels: RuntimeChannels
    controller: EyeCareController
    notifier: RecordingNotifier
    clock: FakeClock


def make_rig(log: RecordingLogHandler, open_settings: Callable[[], None]) -> RuntimeRig:
    clock, notifier = FakeClock(), RecordingNotifier()
    factory = partial(build_coach, clock=clock, notifier=notifier, idle=FakeIdleTimeProvider(0.0))
    store = InMemorySettingsStore(CALIBRATED_SETTINGS)
    controller = EyeCareController(CALIBRATED_SETTINGS, store, factory, notifier, clock, log.logger)
    loop, worker, tray = FakeMainLoop(), FakeCaptureWorker(), FakeTray()
    channels = RuntimeChannels(queue.Queue(), queue.Queue())
    runtime = AppRuntime(loop, controller, worker, tray, channels, open_settings, clock, log.logger)
    return RuntimeRig(runtime, loop, worker, tray, channels, controller, notifier, clock)


@pytest.fixture
def rig(log_recorder: RecordingLogHandler) -> RuntimeRig:
    return make_rig(log_recorder, RecordingCallback())


def test_run_starts_worker_and_tray_and_schedules_pump_and_exit(
    rig: RuntimeRig, log_recorder: RecordingLogHandler
) -> None:
    rig.runtime.run(exit_after_seconds=6.0)
    assert rig.worker.started and rig.tray.started and rig.loop.running
    assert [delay for delay, _ in rig.loop.scheduled] == [6000, AppRuntime.PUMP_INTERVAL_MS]
    assert "tray_started" in log_recorder.events()


def test_pump_camera_status_message_reaches_controller(rig: RuntimeRig) -> None:
    rig.channels.capture.put(CameraStatusChanged(CameraStatus.UNAVAILABLE))
    rig.runtime.pump()
    assert rig.notifier.status is TrayStatus.NO_CAMERA


def test_pump_pause_command_pauses_controller_and_releases_camera(rig: RuntimeRig) -> None:
    rig.channels.commands.put(UserCommand.PAUSE_FOR_HOUR)
    rig.runtime.pump()
    assert rig.controller.is_paused
    assert rig.worker.is_suspended


def test_pump_after_pause_expires_resumes_camera(rig: RuntimeRig) -> None:
    rig.channels.commands.put(UserCommand.PAUSE_FOR_HOUR)
    rig.runtime.pump()
    rig.clock.advance(3600.0)
    rig.runtime.pump()
    assert not rig.controller.is_paused
    assert rig.worker.resumes == 1


def test_pump_open_settings_command_opens_settings_window(
    log_recorder: RecordingLogHandler,
) -> None:
    opener = RecordingCallback()
    rig = make_rig(log_recorder, opener)
    rig.channels.commands.put(UserCommand.OPEN_SETTINGS)
    rig.runtime.pump()
    assert opener.calls == 1


def test_pump_failing_command_logs_and_keeps_pumping(log_recorder: RecordingLogHandler) -> None:
    rig = make_rig(log_recorder, FailingCallback())
    rig.channels.commands.put(UserCommand.OPEN_SETTINGS)
    rig.runtime.pump()
    assert "main_loop_error" in log_recorder.events()
    assert rig.loop.scheduled[-1][0] == AppRuntime.PUMP_INTERVAL_MS


def test_pump_quit_command_stops_everything(
    rig: RuntimeRig, log_recorder: RecordingLogHandler
) -> None:
    rig.channels.commands.put(UserCommand.QUIT)
    rig.runtime.pump()
    assert rig.worker.stopped and rig.tray.stopped and rig.loop.stopped
    assert "app_stopped" in log_recorder.events()
