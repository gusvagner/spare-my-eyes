import sys
from pathlib import Path

from PIL import Image

from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.ui.tray_icon import status_icon_image

ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def write_app_icon(destination: Path) -> None:
    large = status_icon_image(TrayStatus.MONITORING).resize((256, 256), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    large.save(destination, format="ICO", sizes=ICON_SIZES)


if __name__ == "__main__":
    write_app_icon(Path(sys.argv[1]))
