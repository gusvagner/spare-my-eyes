from collections.abc import Callable
from dataclasses import dataclass

import pystray
from PIL import Image, ImageDraw

from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.ui.notification_text import describe_status

_ICON_SIZE = 64
_STATUS_COLORS = {
    TrayStatus.MONITORING: "#2e7d32",
    TrayStatus.PAUSED: "#f9a825",
    TrayStatus.NO_CAMERA: "#9e9e9e",
    TrayStatus.CALIBRATING: "#1565c0",
}


@dataclass(frozen=True, slots=True)
class TrayMenuActions:
    pause_for_hour: Callable[[], None]
    start_break: Callable[[], None]
    recalibrate: Callable[[], None]
    show_camera: Callable[[], None]
    open_settings: Callable[[], None]
    quit: Callable[[], None]


def status_icon_image(status: TrayStatus) -> Image.Image:
    image = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 16, 60, 48), fill=_STATUS_COLORS[status])
    draw.ellipse((24, 22, 40, 42), fill="white")
    return image


class TrayIcon:
    def __init__(self, actions: TrayMenuActions) -> None:
        self._icon = pystray.Icon(
            "spare-my-eyes",
            status_icon_image(TrayStatus.MONITORING),
            describe_status(TrayStatus.MONITORING, None),
            menu=_menu(actions),
        )
        self._shown_status = TrayStatus.MONITORING

    @property
    def title(self) -> str:
        return str(self._icon.title)

    @property
    def image(self) -> Image.Image:
        image: Image.Image = self._icon.icon
        return image

    def menu_labels(self) -> list[str]:
        return [str(item.text) for item in self._icon.menu.items]

    def start(self) -> None:
        self._icon.run_detached()

    def stop(self) -> None:
        self._icon.stop()

    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None:
        if status is not self._shown_status:
            self._icon.icon = status_icon_image(status)
            self._shown_status = status
        title = describe_status(status, blinks_per_minute)
        if title != self._icon.title:
            self._icon.title = title


def _menu(actions: TrayMenuActions) -> pystray.Menu:
    return pystray.Menu(
        pystray.MenuItem("Pause for 1 hour", lambda: actions.pause_for_hour()),
        pystray.MenuItem("Start break now", lambda: actions.start_break()),
        pystray.MenuItem("Recalibrate", lambda: actions.recalibrate()),
        pystray.MenuItem("Show camera", lambda: actions.show_camera()),
        pystray.MenuItem("Settings", lambda: actions.open_settings()),
        pystray.MenuItem("Quit", lambda: actions.quit()),
    )
