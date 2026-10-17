import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui


def read_log_entries(data_dir: Path) -> list[dict[str, object]]:
    lines = (data_dir / "logs" / "spare-my-eyes.log").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_main_scripted_camera_shows_break_card_and_exits_cleanly(tmp_path: Path) -> None:
    settings = {"open_ear_baseline": 0.3, "focal_scale": 660.0, "break_interval_seconds": 2.0}
    (tmp_path / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    command = [
        sys.executable,
        "-m",
        "spare_my_eyes",
        "--scripted-camera",
        "normal",
        "--exit-after",
        "6",
        "--data-dir",
        str(tmp_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stderr
    entries = read_log_entries(tmp_path)
    events = [entry["event"] for entry in entries]
    assert "tray_started" in events
    assert any(
        entry["event"] == "notification_shown" and entry.get("kind") == "break" for entry in entries
    )
    assert events[-1] == "app_stopped"
