import logging
import queue
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from spare_my_eyes.capture.worker import CameraStatusChanged, CaptureMessage
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.structured_log import log_event

PAUSE_SECONDS = 3600.0


class UserCommand(StrEnum):
    PAUSE_FOR_HOUR = "pause_for_hour"
    START_BREAK = "start_break"
    SNOOZE_BREAK = "snooze_break"
    SKIP_BREAK = "skip_break"
    RECALIBRATE = "recalibrate"
    OPEN_SETTINGS = "open_settings"
    QUIT = "quit"


class MainLoop(Protocol):
    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> None: ...

    def run(self) -> None: ...

    def stop(self) -> None: ...


class CaptureControl(Protocol):
    @property
    def is_suspended(self) -> bool: ...

    def start(self) -> None: ...

    def stop(self, timeout_seconds: float = 5.0) -> None: ...

    def suspend(self) -> None: ...

    def resume(self) -> None: ...


class TrayLifecycle(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...


@dataclass(frozen=True, slots=True)
class RuntimeChannels:
    capture: queue.Queue[CaptureMessage]
    commands: queue.Queue[UserCommand]


class AppRuntime:
    """Moves capture messages and user commands onto the main thread and ticks the controller."""

    PUMP_INTERVAL_MS = 50
    MAX_MESSAGES_PER_PUMP = 200
    TICK_SECONDS = 1.0

    def __init__(
        self,
        loop: MainLoop,
        controller: EyeCareController,
        worker: CaptureControl,
        tray: TrayLifecycle,
        channels: RuntimeChannels,
        open_settings: Callable[[], None],
        clock: Clock,
        logger: logging.Logger,
    ) -> None:
        self._loop = loop
        self._controller = controller
        self._worker = worker
        self._tray = tray
        self._channels = channels
        self._open_settings = open_settings
        self._clock = clock
        self._logger = logger
        self._next_tick_at = clock.now()
        self._quitting = False
        self._handlers = self._command_handlers()

    def run(self, exit_after_seconds: float | None) -> None:
        self._worker.start()
        self._tray.start()
        log_event(self._logger, logging.INFO, "tray_started")
        if exit_after_seconds is not None:
            self._loop.schedule(round(exit_after_seconds * 1000), self.quit)
        self._loop.schedule(self.PUMP_INTERVAL_MS, self.pump)
        self._loop.run()

    def quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        self._worker.stop()
        self._tray.stop()
        self._loop.stop()
        log_event(self._logger, logging.INFO, "app_stopped")

    def pump(self) -> None:
        try:
            self._pump_once()
        except Exception:
            self._logger.exception("main_loop_error")
        if not self._quitting:
            self._loop.schedule(self.PUMP_INTERVAL_MS, self.pump)

    def _command_handlers(self) -> dict[UserCommand, Callable[[], None]]:
        return {
            UserCommand.PAUSE_FOR_HOUR: self._pause_for_hour,
            UserCommand.START_BREAK: self._controller.start_break_now,
            UserCommand.SNOOZE_BREAK: self._controller.snooze_break,
            UserCommand.SKIP_BREAK: self._controller.skip_break,
            UserCommand.RECALIBRATE: self._controller.recalibrate,
            UserCommand.OPEN_SETTINGS: self._open_settings,
            UserCommand.QUIT: self.quit,
        }

    def _pump_once(self) -> None:
        self._deliver_capture_messages()
        self._run_commands()
        self._tick_when_due()
        self._resume_capture_after_pause()

    def _deliver_capture_messages(self) -> None:
        for _ in range(self.MAX_MESSAGES_PER_PUMP):
            try:
                message = self._channels.capture.get_nowait()
            except queue.Empty:
                return
            self._deliver(message)

    def _deliver(self, message: CaptureMessage) -> None:
        if isinstance(message, CameraStatusChanged):
            self._controller.on_camera_status(message.status)
            return
        self._controller.on_sample(message)

    def _run_commands(self) -> None:
        while not self._quitting:
            try:
                command = self._channels.commands.get_nowait()
            except queue.Empty:
                return
            self._handlers[command]()

    def _tick_when_due(self) -> None:
        now = self._clock.now()
        if now < self._next_tick_at:
            return
        self._controller.tick()
        self._next_tick_at = now + self.TICK_SECONDS

    def _resume_capture_after_pause(self) -> None:
        if self._worker.is_suspended and not self._controller.is_paused:
            self._worker.resume()

    def _pause_for_hour(self) -> None:
        self._controller.pause_for(PAUSE_SECONDS)
        self._worker.suspend()
