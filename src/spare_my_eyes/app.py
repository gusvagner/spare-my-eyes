import argparse
import logging
import os
import queue
import sys
import tkinter as tk
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from spare_my_eyes.app_runtime import AppRuntime, RuntimeChannels, UserCommand
from spare_my_eyes.capture.scenarios import SCENARIOS
from spare_my_eyes.capture.source_factory import build_sample_source
from spare_my_eyes.capture.worker import CaptureWorker
from spare_my_eyes.clock import Clock, MonotonicClock
from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.coaching.notifier import Notifier
from spare_my_eyes.paths import AppPaths, default_data_dir
from spare_my_eyes.settings import Settings
from spare_my_eyes.settings_editor import SettingsEditor
from spare_my_eyes.settings_store import JsonSettingsStore
from spare_my_eyes.structured_log import configure_file_logging, log_event
from spare_my_eyes.system.idle_time import WindowsIdleTimeProvider
from spare_my_eyes.system.startup_registration import (
    WindowsStartupRegistration,
    installed_executable,
)
from spare_my_eyes.ui.break_card import BreakCard
from spare_my_eyes.ui.card_window import CardWindow
from spare_my_eyes.ui.message_overlay import MessageOverlay
from spare_my_eyes.ui.notification_text import snooze_label
from spare_my_eyes.ui.settings_window import SettingsWindowOpener
from spare_my_eyes.ui.tk_main_loop import TkMainLoop
from spare_my_eyes.ui.tk_notifier import TkNotifier
from spare_my_eyes.ui.tray_icon import TrayIcon, TrayMenuActions


@dataclass(frozen=True, slots=True)
class LaunchOptions:
    data_dir: Path
    scripted_camera: str | None
    exit_after_seconds: float | None


def parse_options(argv: Sequence[str], environment: Mapping[str, str]) -> LaunchOptions:
    parser = argparse.ArgumentParser(prog="spare-my-eyes")
    parser.add_argument("--scripted-camera", choices=sorted(SCENARIOS), default=None)
    parser.add_argument("--exit-after", type=float, default=None, metavar="SECONDS")
    parser.add_argument("--data-dir", type=Path, default=None)
    arguments = parser.parse_args(list(argv))
    data_dir: Path = arguments.data_dir or default_data_dir(environment)
    scripted_camera: str | None = arguments.scripted_camera
    exit_after: float | None = arguments.exit_after
    return LaunchOptions(data_dir, scripted_camera, exit_after)


def main(argv: Sequence[str] | None = None) -> int:
    options = parse_options(sys.argv[1:] if argv is None else argv, os.environ)
    paths = AppPaths(options.data_dir)
    logger = configure_file_logging(paths.log_dir)
    log_event(logger, logging.INFO, "app_started", scripted_camera=options.scripted_camera)
    try:
        _run_app(options, paths, logger)
    except Exception:
        logger.exception("app_crashed")
        return 1
    return 0


def _run_app(options: LaunchOptions, paths: AppPaths, logger: logging.Logger) -> None:
    root = tk.Tk()
    root.withdraw()
    runtime = _build_runtime(root, options, paths, logger)
    runtime.run(options.exit_after_seconds)
    root.destroy()


def _build_runtime(
    root: tk.Tk, options: LaunchOptions, paths: AppPaths, logger: logging.Logger
) -> AppRuntime:
    clock = MonotonicClock()
    channels = RuntimeChannels(queue.Queue(), queue.Queue())
    store = JsonSettingsStore(paths.settings_file, logger)
    settings = store.load()
    tray = TrayIcon(_tray_actions(channels.commands))
    notifier = _build_notifier(root, tray, channels.commands, settings, logger)
    controller = _build_controller(settings, store, notifier, clock, logger)
    source = build_sample_source(options.scripted_camera, settings, clock, logger)
    worker = CaptureWorker(source, channels.capture, settings.camera_retry_seconds, logger)
    open_settings = _settings_opener(root, controller, store)
    loop = TkMainLoop(root)
    return AppRuntime(loop, controller, worker, tray, channels, open_settings, clock, logger)


def _build_controller(
    settings: Settings,
    store: JsonSettingsStore,
    notifier: Notifier,
    clock: Clock,
    logger: logging.Logger,
) -> EyeCareController:
    factory = partial(build_coach, clock=clock, notifier=notifier, idle=WindowsIdleTimeProvider())
    return EyeCareController(settings, store, factory, notifier, clock, logger)


def _settings_opener(
    root: tk.Tk, controller: EyeCareController, store: JsonSettingsStore
) -> SettingsWindowOpener:
    editor = SettingsEditor(controller, WindowsStartupRegistration(installed_executable()))
    return SettingsWindowOpener(root, editor, lambda: os.startfile(store.ensure_file()))


def _build_notifier(
    root: tk.Tk,
    tray: TrayIcon,
    commands: queue.Queue[UserCommand],
    settings: Settings,
    logger: logging.Logger,
) -> TkNotifier:
    break_card = BreakCard(
        root,
        snooze_label(settings.snooze_seconds),
        lambda: commands.put(UserCommand.SNOOZE_BREAK),
        lambda: commands.put(UserCommand.SKIP_BREAK),
    )
    nudge, distance = MessageOverlay(root, 0), MessageOverlay(root, 1)
    return TkNotifier(nudge, distance, break_card.card, CardWindow(root), tray, logger)


def _tray_actions(commands: queue.Queue[UserCommand]) -> TrayMenuActions:
    return TrayMenuActions(
        pause_for_hour=lambda: commands.put(UserCommand.PAUSE_FOR_HOUR),
        start_break=lambda: commands.put(UserCommand.START_BREAK),
        recalibrate=lambda: commands.put(UserCommand.RECALIBRATE),
        open_settings=lambda: commands.put(UserCommand.OPEN_SETTINGS),
        quit=lambda: commands.put(UserCommand.QUIT),
    )
