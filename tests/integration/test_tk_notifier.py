import tkinter as tk
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from spare_my_eyes.calibration import CalibrationProgress, CalibrationStep
from spare_my_eyes.coaching.break_session import BreakProgress, BreakStep
from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.ui.break_card import BreakCard
from spare_my_eyes.ui.card_window import CardWindow
from spare_my_eyes.ui.message_overlay import MessageOverlay
from spare_my_eyes.ui.tk_notifier import TkNotifier
from spare_my_eyes.ui.window_style import is_foreground
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.tray import FakeTray

pytestmark = pytest.mark.gui

LOOKING_OUT = BreakProgress(BreakStep.LOOK_OUT, 3.0, 20.0, 0, 5, True)


@dataclass
class UiRig:
    notifier: TkNotifier
    nudge: MessageOverlay
    distance: MessageOverlay
    break_card: BreakCard
    calibration: CardWindow
    tray: FakeTray
    presses: list[str]


@pytest.fixture
def rig(tk_root: tk.Tk, log_recorder: RecordingLogHandler) -> Iterator[UiRig]:
    root = tk_root
    presses: list[str] = []
    nudge, distance = MessageOverlay(root, 0), MessageOverlay(root, 1)
    card = BreakCard(
        root, "Snooze 5 min", lambda: presses.append("snooze"), lambda: presses.append("skip")
    )
    calibration, tray = CardWindow(root), FakeTray()
    notifier = TkNotifier(nudge, distance, card.card, calibration, tray, log_recorder.logger)
    yield UiRig(notifier, nudge, distance, card, calibration, tray, presses)
    for window in (nudge.window, distance.window, card.card.window, calibration.window):
        window.destroy()


def test_show_blink_nudge_shows_overlay_with_message_without_taking_focus(rig: UiRig) -> None:
    rig.notifier.show_blink_nudge("Blink")
    assert rig.nudge.is_visible
    assert rig.nudge.text == "Blink"
    assert not is_foreground(rig.nudge.window)


def test_hide_blink_nudge_hides_overlay(rig: UiRig) -> None:
    rig.notifier.show_blink_nudge("Blink")
    rig.notifier.hide_blink_nudge()
    assert not rig.nudge.is_visible


def test_show_blink_nudge_repeated_logs_shown_once(
    rig: UiRig, log_recorder: RecordingLogHandler
) -> None:
    rig.notifier.show_blink_nudge("Blink")
    rig.notifier.show_blink_nudge("Blink")
    assert log_recorder.events().count("notification_shown") == 1


def test_show_distance_alert_uses_its_own_overlay(rig: UiRig) -> None:
    rig.notifier.show_distance_alert("Move back a little")
    assert rig.distance.is_visible
    assert not rig.nudge.is_visible


def test_show_break_shows_card_and_buttons_call_back(rig: UiRig) -> None:
    rig.notifier.show_break(LOOKING_OUT)
    assert rig.break_card.card.is_visible
    assert rig.break_card.card.title == "Look out the window"
    rig.break_card.snooze_button.invoke()
    rig.break_card.skip_button.invoke()
    assert rig.presses == ["snooze", "skip"]


def test_hide_break_hides_card(rig: UiRig) -> None:
    rig.notifier.show_break(LOOKING_OUT)
    rig.notifier.hide_break()
    assert not rig.break_card.card.is_visible


def test_show_calibration_shows_instruction(rig: UiRig) -> None:
    rig.notifier.show_calibration(CalibrationProgress(CalibrationStep.LOOK_AT_SCREEN, 8.0))
    assert rig.calibration.is_visible
    assert "Look at the screen" in rig.calibration.title


def test_set_status_forwards_to_tray(rig: UiRig) -> None:
    rig.notifier.set_status(TrayStatus.PAUSED, None)
    assert rig.tray.statuses == [(TrayStatus.PAUSED, None)]
