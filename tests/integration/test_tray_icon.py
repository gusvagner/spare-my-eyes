import pytest

from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.ui.tray_icon import TrayIcon, TrayMenuActions, status_icon_image

pytestmark = pytest.mark.gui


def do_nothing() -> None:
    return None


ACTIONS = TrayMenuActions(do_nothing, do_nothing, do_nothing, do_nothing, do_nothing, do_nothing)


def test_menu_labels_match_spec() -> None:
    assert TrayIcon(ACTIONS).menu_labels() == [
        "Pause for 1 hour",
        "Start break now",
        "Recalibrate",
        "Show camera",
        "Settings",
        "Quit",
    ]


def test_set_status_updates_tooltip_with_rate() -> None:
    tray = TrayIcon(ACTIONS)
    tray.set_status(TrayStatus.MONITORING, 9.0)
    assert tray.title == "Spare My Eyes: monitoring, 9 blinks/min"


def test_status_icon_image_differs_per_status() -> None:
    monitoring = status_icon_image(TrayStatus.MONITORING).getpixel((8, 32))
    no_camera = status_icon_image(TrayStatus.NO_CAMERA).getpixel((8, 32))
    assert monitoring != no_camera


def test_set_status_unchanged_status_keeps_the_same_image() -> None:
    tray = TrayIcon(ACTIONS)
    tray.set_status(TrayStatus.PAUSED, None)
    first = tray.image
    tray.set_status(TrayStatus.PAUSED, None)
    assert tray.image is first
