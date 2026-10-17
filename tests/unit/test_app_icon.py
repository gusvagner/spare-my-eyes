from pathlib import Path

from PIL import Image

from spare_my_eyes.ui.app_icon import write_app_icon


def test_write_app_icon_creates_multi_size_ico(tmp_path: Path) -> None:
    destination = tmp_path / "SpareMyEyes.ico"
    write_app_icon(destination)
    with Image.open(destination) as icon:
        assert icon.format == "ICO"
        assert (16, 16) in icon.info["sizes"]
        assert (256, 256) in icon.info["sizes"]
