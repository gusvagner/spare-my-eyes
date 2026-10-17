import logging
from typing import Protocol

from spare_my_eyes.calibration import CalibrationProgress
from spare_my_eyes.coaching.break_session import BreakProgress
from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.structured_log import log_event
from spare_my_eyes.ui.card_window import CardWindow
from spare_my_eyes.ui.message_overlay import MessageOverlay
from spare_my_eyes.ui.notification_text import CardText, describe_break, describe_calibration


class TrayStatusView(Protocol):
    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None: ...


class TkNotifier:
    def __init__(
        self,
        nudge: MessageOverlay,
        distance: MessageOverlay,
        break_card: CardWindow,
        calibration_card: CardWindow,
        tray: TrayStatusView,
        logger: logging.Logger,
    ) -> None:
        self._nudge = nudge
        self._distance = distance
        self._break_card = break_card
        self._calibration_card = calibration_card
        self._tray = tray
        self._logger = logger

    def show_blink_nudge(self, message: str) -> None:
        self._show_message(self._nudge, message, "blink_nudge")

    def hide_blink_nudge(self) -> None:
        self._nudge.hide()

    def show_distance_alert(self, message: str) -> None:
        self._show_message(self._distance, message, "distance_alert")

    def hide_distance_alert(self) -> None:
        self._distance.hide()

    def show_break(self, progress: BreakProgress) -> None:
        self._show_card(self._break_card, describe_break(progress), "break")

    def hide_break(self) -> None:
        self._break_card.hide()

    def show_calibration(self, progress: CalibrationProgress) -> None:
        self._show_card(self._calibration_card, describe_calibration(progress), "calibration")

    def hide_calibration(self) -> None:
        self._calibration_card.hide()

    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None:
        self._tray.set_status(status, blinks_per_minute)

    def _show_message(self, overlay: MessageOverlay, message: str, kind: str) -> None:
        if not overlay.is_visible:
            log_event(self._logger, logging.INFO, "notification_shown", kind=kind)
        overlay.show(message)

    def _show_card(self, card: CardWindow, text: CardText, kind: str) -> None:
        if not card.is_visible:
            log_event(self._logger, logging.INFO, "notification_shown", kind=kind)
        card.show(text)
