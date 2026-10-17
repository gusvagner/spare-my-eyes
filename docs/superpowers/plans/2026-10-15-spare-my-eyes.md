# Spare My Eyes v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows tray app that measures blink rate, blink completeness, screen distance and head pose from the webcam, locally, and nudges the user only when their eyes need it.

**Architecture:** One Python process. A capture thread turns webcam frames into `FaceSample`s (OpenCV + MediaPipe) and drops each frame immediately. The main thread runs pure analyzers, three coaching policies (blink nudge, distance alert, verified break) composed by a `Coach`, and an `EyeCareController` that runs calibration first. The UI (tkinter overlays, pystray tray) sits behind a `Notifier` interface, so the whole behavior is tested with fakes and a scripted face-sample timeline.

**Tech Stack:** Python 3.12, uv, OpenCV (`opencv-python`), MediaPipe Face Landmarker task, tkinter, pystray, Pillow, pytest, ruff, mypy (strict), PyInstaller, Inno Setup 6 (per-user installer), GitHub Actions (`windows-latest`).

**Spec:** `docs/superpowers/specs/2026-10-15-spare-my-eyes-design.md`

## Global Constraints

- Platform: Windows 10/11. Python 3.12 exactly: `requires-python = ">=3.12,<3.13"`.
- All processing local. Frames live only in memory and are discarded as soon as the `FaceSample` is produced. Nothing is written to disk except `settings.json` and logs.
- No cloud service, telemetry or account.
- Code, README and UI text in English. MIT license.
- Third-party libraries (OpenCV, MediaPipe, pystray, tkinter, Win32 via ctypes) are used only inside adapter classes owned by the project, and are injected through constructors.
- One test command: `uv run pytest`. CI runs `ruff format --check`, `ruff check`, `mypy` (strict) and `pytest` on `windows-latest` on every push and pull request.
- TDD: every piece of production code starts with a test that fails for the expected reason.
- Test names follow `method_scenario_expected_result`, written as `test_<method>_<scenario>_<expected_result>`.
- Test doubles are named classes in `tests/fakes/`. No inline stubs, no `unittest.mock`.
- No comments in code. A class docstring only when the class name does not explain its purpose.
- Functions 4–20 lines, files under 500 lines, at most 2 levels of indentation, early returns, explicit types everywhere (mypy strict, no `Any` in our own signatures).
- Exception messages include the offending value and the expected shape.
- Logs are structured JSON lines written through `log_event(...)` to `%APPDATA%\SpareMyEyes\logs\spare-my-eyes.log`.
- Settings live in `%APPDATA%\SpareMyEyes\settings.json`. Defaults live in code; the file holds only overrides.
- Exact UI copy: `Blink`, `Blink slowly, close fully`, `Move back a little`, `Look out the window`, `Snooze 5 min`, `Skip`; tray menu `Pause for 1 hour`, `Start break now`, `Recalibrate`, `Settings`, `Quit`; settings window `Spare My Eyes settings`, `Window side`, `Break every (minutes)`, `Blink alert below (blinks/min)`, `Too close below (cm)`, `Camera number (applies after restart)`, `Start with Windows`, `Open settings file`, `Cancel`, `Save`.
- Behavior numbers (spec §5): blink starts below 80% of baseline EAR, complete below 40%, spontaneous ≤ 500 ms; nudge below 8 blinks/min over 2 min of presence, slow-blink wording above 30% incomplete, hide after 2 complete blinks or 8 s, cooldown 3 min; distance alert below 50 cm for 30 s, clear above 55 cm, cooldown 5 min; break every 20 min of screen time, 20 s gaze at ≥ 25° toward the window, 5 slow blinks below 40% for ≥ 300 ms, snooze 5 min, 2 min without interaction times out; absences < 5 min pause the counter, ≥ 5 min reset it; no face for 1 min means absent; camera retry every 60 s.
- Before every commit run `uv run ruff format . && uv run ruff check --fix .`, then `uv run mypy`. Import order and line wrapping in this plan's snippets are indicative; ruff decides.
- Commit at the end of every task. Commit messages end with:
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`

## Review Focus

1. **Face never detected while the user keeps typing** (dim room, camera pointed badly, user sits off-frame). Expected: breaks still arrive, driven by keyboard/mouse activity, as unverified breaks. Pinned in Task 16 (`test_break_face_never_detected_but_user_typing_still_gets_unverified_break`).
2. **Hand-edited `settings.json` with a wrong type, a negative number, `true` for a number, or an unknown key.** Expected: only that value falls back to its default, the rest of the file is honored, and the problem is logged. Pinned in Task 8.
3. **Running from source without downloading the MediaPipe model.** Expected: the app starts with the gray "no camera" icon, logs `model_missing`, and keeps time-based breaks; it does not crash. Pinned in Task 20 (`test_build_sample_source_missing_model_returns_unavailable_source`).
4. **The PC sleeps or hibernates for an hour** (monotonic clock jumps, no samples or ticks in between). Expected: no 8-hour jump in screen time, the long gap counts as an absence ≥ 5 min and resets the counter, no break pops up right after wake. Pinned in Task 7 and Task 16 (`test_break_sleep_gap_resets_screen_time`).
5. **Webcam unplugged or the user pauses while a nudge, alert or break card is on screen.** Expected: every overlay hides; nothing stays stuck on screen. Pinned in Task 16 (`test_camera_unplugged_hides_visible_blink_nudge`, `test_pause_hides_open_break_card`).

---

## File Structure

```
spare-my-eyes/
├─ pyproject.toml                      uv project, ruff, mypy, pytest config
├─ uv.lock
├─ README.md
├─ LICENSE
├─ .gitignore
├─ .github/workflows/ci.yml            ruff + mypy + pytest on windows-latest
├─ .github/workflows/release.yml       v* tag → installer + portable zip on the GitHub Release
├─ packaging/launcher.py               PyInstaller entry point
├─ packaging/installer.iss             Inno Setup per-user installer
├─ docs/manual-test-checklist.md
├─ src/spare_my_eyes/
│  ├─ __init__.py                      __version__
│  ├─ __main__.py                      python -m spare_my_eyes
│  ├─ py.typed
│  ├─ app.py                           argument parsing + composition root
│  ├─ app_runtime.py                   Tk loop: drains capture queue and user commands
│  ├─ paths.py                         %APPDATA%\SpareMyEyes layout
│  ├─ structured_log.py                JSON log formatter, log_event
│  ├─ clock.py                         Clock, MonotonicClock
│  ├─ settings.py                      Settings, parsing overrides
│  ├─ settings_store.py                SettingsStore, JsonSettingsStore
│  ├─ settings_form.py                 settings window form: parse, validate, apply
│  ├─ settings_editor.py               SettingsEditor (form → controller + startup entry)
│  ├─ calibration.py                   CalibrationSession
│  ├─ model_asset.py                   face_landmarker.task download + SHA-256 check
│  ├─ assets/face_landmarker.task      downloaded, git-ignored
│  ├─ capture/
│  │  ├─ face_sample.py                FaceSample
│  │  ├─ geometry.py                   EAR, iris diameter, yaw
│  │  ├─ camera_errors.py              CameraUnavailableError, CameraBusyError
│  │  ├─ sample_source.py              FaceSampleSource, CameraStatus, UnavailableSampleSource
│  │  ├─ scripted.py                   TimelineSegment, generate_samples, ScriptedFaceSampleSource
│  │  ├─ scenarios.py                  named scripted timelines
│  │  ├─ frame_source.py               Frame, FrameSource
│  │  ├─ opencv_frame_source.py        OpenCvFrameSource
│  │  ├─ landmarker.py                 FaceLandmarkDetector
│  │  ├─ mediapipe_landmarker.py       MediaPipeFaceLandmarker
│  │  ├─ camera_sample_source.py       CameraFaceSampleSource
│  │  ├─ source_factory.py             build_sample_source
│  │  └─ worker.py                     CaptureWorker, CameraStatusChanged
│  ├─ analysis/
│  │  ├─ blink_detector.py             Blink, BlinkKind, BlinkDetector
│  │  ├─ blink_rate.py                 BlinkRateMonitor, BlinkStats
│  │  ├─ distance.py                   ScreenDistanceEstimator
│  │  ├─ gaze.py                       WindowSide, WindowGazeDetector
│  │  └─ presence.py                   PresenceTracker
│  ├─ coaching/
│  │  ├─ notifier.py                   Notifier, TrayStatus
│  │  ├─ cooldown.py                   Cooldown
│  │  ├─ screen_time.py                ScreenTimeCounter
│  │  ├─ break_session.py              BreakSession, BreakProgress
│  │  ├─ blink_nudge.py                BlinkNudgePolicy
│  │  ├─ distance_alert.py             DistanceAlertPolicy
│  │  ├─ break_policy.py               BreakPolicy
│  │  ├─ coach.py                      Coach, CoachingPolicy
│  │  ├─ factory.py                    build_coach
│  │  └─ controller.py                 EyeCareController
│  ├─ system/idle_time.py              IdleTimeProvider, WindowsIdleTimeProvider
│  ├─ system/startup_registration.py   start with Windows (HKCU Run value)
│  └─ ui/
│     ├─ notification_text.py          pure text for cards and tooltip
│     ├─ window_style.py               Win32 no-focus show/hide
│     ├─ message_overlay.py            MessageOverlay (blink nudge, distance alert)
│     ├─ break_card.py                 BreakCard
│     ├─ calibration_card.py           CalibrationCard
│     ├─ tray_icon.py                  TrayIcon
│     ├─ tk_notifier.py                TkNotifier
│     ├─ settings_window.py            SettingsWindow, SettingsWindowOpener
│     ├─ tk_main_loop.py               TkMainLoop
│     └─ app_icon.py                   .ico for the exe and installer
└─ tests/
   ├─ conftest.py
   ├─ fakes/                           named test doubles
   ├─ unit/
   ├─ integration/
   └─ fixtures/faces/ + CREDITS.md
```

Every package directory (`capture/`, `analysis/`, `coaching/`, `system/`, `ui/`, `tests/`, `tests/fakes/`, `tests/unit/`, `tests/integration/`) gets an empty `__init__.py` the first time a task creates a file in it.

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `LICENSE`, `README.md`
- Create: `src/spare_my_eyes/__init__.py`, `src/spare_my_eyes/py.typed`
- Create: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/fakes/__init__.py`
- Test: `tests/unit/test_package.py`

**Interfaces:**
- Produces: package `spare_my_eyes` with `__version__: str`; `tests.fakes` importable from tests.

- [ ] **Step 1: Install uv and Python 3.12**

Run in PowerShell (free, no cost):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Open a new terminal, then:

```bash
uv --version
uv python install 3.12
```

Expected: a uv version is printed and Python 3.12 is installed.

- [ ] **Step 2: Initialize git**

```bash
cd /c/labs/spare-my-eyes
git init -b main
```

- [ ] **Step 3: Write the project files**

`pyproject.toml`:

```toml
[project]
name = "spare-my-eyes"
version = "0.1.0"
description = "A Windows tray app that watches how you blink and nudges you only when your eyes need it."
readme = "README.md"
license = "MIT"
requires-python = ">=3.12,<3.13"
dependencies = [
    "mediapipe>=0.10.14",
    "numpy>=1.26",
    "opencv-python>=4.10",
    "pillow>=10.4",
    "pystray>=0.19.5",
]

[project.scripts]
spare-my-eyes = "spare_my_eyes.app:main"

[dependency-groups]
dev = [
    "mypy>=1.11",
    "pyinstaller>=6.10",
    "pytest>=8.3",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/spare_my_eyes"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-ra --strict-markers"
markers = [
    "mediapipe: runs the real MediaPipe Face Landmarker model",
    "gui: creates real Tk windows or a tray icon",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "N", "SIM", "RUF"]

[tool.mypy]
strict = true
python_version = "3.12"
files = ["src", "tests"]

[[tool.mypy.overrides]]
module = ["mediapipe.*", "pystray.*", "cv2.*"]
ignore_missing_imports = true
```

`.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
build/
dist/
*.spec
src/spare_my_eyes/assets/*.task
src/spare_my_eyes/assets/*.download
```

`LICENSE`: the standard MIT license text with the line `Copyright (c) 2026 Spare My Eyes contributors`.

`README.md` (expanded in Task 23):

```markdown
# Spare My Eyes

A Windows tray app that watches how you blink and nudges you only when your eyes need it.
```

Create empty files: `src/spare_my_eyes/__init__.py`, `src/spare_my_eyes/py.typed`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/fakes/__init__.py`.

- [ ] **Step 4: Write the failing test**

`tests/unit/test_package.py`:

```python
import spare_my_eyes


def test_version_installed_package_is_0_1_0() -> None:
    assert spare_my_eyes.__version__ == "0.1.0"
```

- [ ] **Step 5: Install and run the test to see it fail**

```bash
uv sync
uv run pytest tests/unit/test_package.py -v
```

Expected: FAIL with `AttributeError: module 'spare_my_eyes' has no attribute '__version__'`.

- [ ] **Step 6: Write the minimal implementation**

`src/spare_my_eyes/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 7: Run all checks**

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy
```

Expected: 1 passed; ruff and mypy report no issues.

- [ ] **Step 8: Commit**

```bash
git add .
git commit -m "chore: scaffold uv project with pytest, ruff and mypy

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Clock and FaceSample

**Files:**
- Create: `src/spare_my_eyes/clock.py`
- Create: `src/spare_my_eyes/capture/__init__.py`, `src/spare_my_eyes/capture/face_sample.py`
- Create: `tests/fakes/clock.py`
- Test: `tests/unit/test_clock.py`, `tests/unit/test_face_sample.py`

**Interfaces:**
- Produces:
  - `Clock` protocol: `now() -> float` (monotonic seconds); `MonotonicClock`.
  - `FaceSample(timestamp: float, face_present: bool, left_ear: float = 0.0, right_ear: float = 0.0, iris_diameter_px: float = 0.0, head_yaw_degrees: float = 0.0)`, frozen; property `mean_ear -> float`; classmethod `absent(timestamp: float) -> FaceSample`.
  - Fake `tests.fakes.clock.FakeClock(start: float = 0.0)` with `now()`, `advance(seconds)`, `set(timestamp)`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_clock.py`:

```python
from spare_my_eyes.clock import MonotonicClock


def test_now_called_twice_never_goes_backwards() -> None:
    clock = MonotonicClock()
    first = clock.now()
    assert clock.now() >= first
```

`tests/unit/test_face_sample.py`:

```python
import pytest

from spare_my_eyes.capture.face_sample import FaceSample


def test_mean_ear_two_eyes_returns_average() -> None:
    sample = FaceSample(timestamp=1.0, face_present=True, left_ear=0.2, right_ear=0.3)
    assert sample.mean_ear == pytest.approx(0.25)


def test_absent_any_timestamp_has_no_face_and_zero_measurements() -> None:
    assert FaceSample.absent(5.0) == FaceSample(timestamp=5.0, face_present=False)
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_clock.py tests/unit/test_face_sample.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.clock'` and `... 'spare_my_eyes.capture'`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/clock.py`:

```python
import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float: ...


class MonotonicClock:
    def now(self) -> float:
        return time.monotonic()
```

`src/spare_my_eyes/capture/__init__.py`: empty.

`src/spare_my_eyes/capture/face_sample.py`:

```python
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class FaceSample:
    timestamp: float
    face_present: bool
    left_ear: float = 0.0
    right_ear: float = 0.0
    iris_diameter_px: float = 0.0
    head_yaw_degrees: float = 0.0

    @property
    def mean_ear(self) -> float:
        return (self.left_ear + self.right_ear) / 2

    @classmethod
    def absent(cls, timestamp: float) -> Self:
        return cls(timestamp=timestamp, face_present=False)
```

`tests/fakes/clock.py`:

```python
class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError(f"FakeClock cannot move backwards by {seconds} s; expected >= 0")
        self._now += seconds

    def set(self, timestamp: float) -> None:
        if timestamp < self._now:
            raise ValueError(
                f"FakeClock cannot move back to {timestamp}; expected >= current {self._now}"
            )
        self._now = timestamp
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit -v && uv run mypy`
Expected: all passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/clock.py src/spare_my_eyes/capture tests/fakes/clock.py tests/unit/test_clock.py tests/unit/test_face_sample.py
git commit -m "feat: add clock abstraction and FaceSample

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Face geometry (EAR, iris diameter, yaw)

**Files:**
- Create: `src/spare_my_eyes/capture/geometry.py`
- Test: `tests/unit/test_geometry.py`

**Interfaces:**
- Produces:
  - `Point = tuple[float, float]` (pixel coordinates).
  - `eye_aspect_ratio(contour: Sequence[Point]) -> float`: contour is p1..p6 (corner, upper, upper, corner, lower, lower); returns `(|p2-p6| + |p3-p5|) / (2·|p1-p4|)`.
  - `iris_diameter(boundary: Sequence[Point]) -> float`: boundary is (right, top, left, bottom); returns the mean of the horizontal and vertical diameters.
  - `yaw_degrees(rotation: Sequence[Sequence[float]]) -> float`: rotation about the vertical axis of a 3×3 rotation matrix, `atan2(r[0][2], r[2][2])` in degrees.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_geometry.py`:

```python
import math

import pytest

from spare_my_eyes.capture.geometry import eye_aspect_ratio, iris_diameter, yaw_degrees


def test_eye_aspect_ratio_open_eye_returns_height_over_twice_width() -> None:
    contour = [(0.0, 0.0), (1.0, -1.0), (3.0, -1.0), (4.0, 0.0), (3.0, 1.0), (1.0, 1.0)]
    assert eye_aspect_ratio(contour) == pytest.approx(0.5)


def test_eye_aspect_ratio_closed_eye_returns_zero() -> None:
    contour = [(0.0, 0.0), (1.0, 0.0), (3.0, 0.0), (4.0, 0.0), (3.0, 0.0), (1.0, 0.0)]
    assert eye_aspect_ratio(contour) == pytest.approx(0.0)


def test_eye_aspect_ratio_wrong_point_count_raises_value_error() -> None:
    with pytest.raises(ValueError, match="6 points"):
        eye_aspect_ratio([(0.0, 0.0)] * 5)


def test_eye_aspect_ratio_coincident_corners_raises_value_error() -> None:
    contour = [(2.0, 0.0), (1.0, -1.0), (3.0, -1.0), (2.0, 0.0), (3.0, 1.0), (1.0, 1.0)]
    with pytest.raises(ValueError, match="corners"):
        eye_aspect_ratio(contour)


def test_iris_diameter_circle_boundary_returns_diameter() -> None:
    boundary = [(15.0, 10.0), (10.0, 5.0), (5.0, 10.0), (10.0, 15.0)]
    assert iris_diameter(boundary) == pytest.approx(10.0)


def test_iris_diameter_wrong_point_count_raises_value_error() -> None:
    with pytest.raises(ValueError, match="4 points"):
        iris_diameter([(0.0, 0.0)] * 3)


@pytest.mark.parametrize("angle", [-40.0, 0.0, 30.0])
def test_yaw_degrees_rotation_about_vertical_axis_returns_angle(angle: float) -> None:
    radians = math.radians(angle)
    rotation = [
        [math.cos(radians), 0.0, math.sin(radians)],
        [0.0, 1.0, 0.0],
        [-math.sin(radians), 0.0, math.cos(radians)],
    ]
    assert yaw_degrees(rotation) == pytest.approx(angle)


def test_yaw_degrees_non_3x3_matrix_raises_value_error() -> None:
    with pytest.raises(ValueError, match="3x3"):
        yaw_degrees([[1.0, 0.0], [0.0, 1.0]])
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_geometry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.capture.geometry'`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/capture/geometry.py`:

```python
import math
from collections.abc import Sequence

Point = tuple[float, float]


def eye_aspect_ratio(contour: Sequence[Point]) -> float:
    if len(contour) != 6:
        raise ValueError(f"Eye contour needs 6 points (p1..p6), got {len(contour)}: {contour!r}")
    p1, p2, p3, p4, p5, p6 = contour
    width = math.dist(p1, p4)
    if width == 0:
        raise ValueError(f"Eye corners p1 and p4 coincide at {p1!r}; expected distinct points")
    return (math.dist(p2, p6) + math.dist(p3, p5)) / (2 * width)


def iris_diameter(boundary: Sequence[Point]) -> float:
    if len(boundary) != 4:
        raise ValueError(
            f"Iris boundary needs 4 points (right, top, left, bottom), got {len(boundary)}: "
            f"{boundary!r}"
        )
    right, top, left, bottom = boundary
    return (math.dist(right, left) + math.dist(top, bottom)) / 2


def yaw_degrees(rotation: Sequence[Sequence[float]]) -> float:
    if len(rotation) != 3 or any(len(row) != 3 for row in rotation):
        raise ValueError(f"Rotation must be a 3x3 matrix, got {rotation!r}")
    return math.degrees(math.atan2(rotation[0][2], rotation[2][2]))
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit/test_geometry.py -v && uv run mypy`
Expected: 10 passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/capture/geometry.py tests/unit/test_geometry.py
git commit -m "feat: add eye aspect ratio, iris diameter and yaw geometry

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: BlinkDetector

**Files:**
- Create: `src/spare_my_eyes/analysis/__init__.py`, `src/spare_my_eyes/analysis/blink_detector.py`
- Create: `tests/fakes/samples.py`
- Test: `tests/unit/test_blink_detector.py`

**Interfaces:**
- Consumes: `FaceSample` (Task 2).
- Produces:
  - `BlinkKind` (StrEnum): `COMPLETE`, `INCOMPLETE`, `DELIBERATE`.
  - `Blink(ended_at: float, duration_seconds: float, min_ear_ratio: float, kind: BlinkKind)`, frozen; property `is_spontaneous -> bool` (false for `DELIBERATE`).
  - `BlinkThresholds(closing_ratio=0.8, complete_ratio=0.4, max_spontaneous_seconds=0.5)`, frozen; `DEFAULT_BLINK_THRESHOLDS`.
  - `BlinkDetector(open_ear_baseline: float, thresholds: BlinkThresholds = BlinkThresholds())` with `update(sample: FaceSample) -> Blink | None` and `reset() -> None`.
  - Fake helpers in `tests.fakes.samples`: `samples_from_ears(ears, fps=20.0, start=0.0, iris_diameter_px=11.0, head_yaw_degrees=0.0) -> list[FaceSample]`; `blink_of(kind: BlinkKind, ended_at: float = 0.0) -> Blink`.

A blink's duration runs from the first closed sample to the first open sample after it.

- [ ] **Step 1: Write the test helpers**

`tests/fakes/samples.py`:

```python
from collections.abc import Sequence

from spare_my_eyes.analysis.blink_detector import Blink, BlinkKind
from spare_my_eyes.capture.face_sample import FaceSample


def samples_from_ears(
    ears: Sequence[float],
    fps: float = 20.0,
    start: float = 0.0,
    iris_diameter_px: float = 11.0,
    head_yaw_degrees: float = 0.0,
) -> list[FaceSample]:
    return [
        FaceSample(
            timestamp=start + index / fps,
            face_present=True,
            left_ear=ear,
            right_ear=ear,
            iris_diameter_px=iris_diameter_px,
            head_yaw_degrees=head_yaw_degrees,
        )
        for index, ear in enumerate(ears)
    ]


def blink_of(kind: BlinkKind, ended_at: float = 0.0) -> Blink:
    return Blink(ended_at=ended_at, duration_seconds=0.15, min_ear_ratio=0.2, kind=kind)
```

- [ ] **Step 2: Write the failing tests**

`tests/unit/test_blink_detector.py`:

```python
from collections.abc import Iterable

import pytest

from spare_my_eyes.analysis.blink_detector import Blink, BlinkDetector, BlinkKind
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import blink_of, samples_from_ears

BASELINE = 0.30


def detect_all(detector: BlinkDetector, samples: Iterable[FaceSample]) -> list[Blink]:
    return [blink for sample in samples if (blink := detector.update(sample)) is not None]


def test_update_short_deep_closure_reports_complete_blink() -> None:
    blinks = detect_all(BlinkDetector(BASELINE), samples_from_ears([0.30, 0.18, 0.06, 0.18, 0.30]))
    assert len(blinks) == 1
    assert blinks[0].kind is BlinkKind.COMPLETE
    assert blinks[0].duration_seconds == pytest.approx(0.15)
    assert blinks[0].min_ear_ratio == pytest.approx(0.2)
    assert blinks[0].ended_at == pytest.approx(0.2)


def test_update_short_shallow_closure_reports_incomplete_blink() -> None:
    blinks = detect_all(BlinkDetector(BASELINE), samples_from_ears([0.30, 0.20, 0.15, 0.20, 0.30]))
    assert [blink.kind for blink in blinks] == [BlinkKind.INCOMPLETE]


def test_update_closure_longer_than_half_second_reports_deliberate_closure() -> None:
    ears = [0.30] + [0.05] * 12 + [0.30]
    blinks = detect_all(BlinkDetector(BASELINE), samples_from_ears(ears))
    assert [blink.kind for blink in blinks] == [BlinkKind.DELIBERATE]


def test_update_eyes_open_reports_nothing() -> None:
    assert detect_all(BlinkDetector(BASELINE), samples_from_ears([0.30] * 40)) == []


def test_update_face_lost_mid_blink_discards_blink() -> None:
    samples = [
        *samples_from_ears([0.30, 0.06]),
        FaceSample.absent(0.10),
        *samples_from_ears([0.30], start=0.15),
    ]
    assert detect_all(BlinkDetector(BASELINE), samples) == []


def test_reset_mid_blink_discards_blink() -> None:
    detector = BlinkDetector(BASELINE)
    detect_all(detector, samples_from_ears([0.30, 0.06]))
    detector.reset()
    assert detect_all(detector, samples_from_ears([0.30], start=0.10)) == []


def test_init_non_positive_baseline_raises_value_error() -> None:
    with pytest.raises(ValueError, match="open_ear_baseline"):
        BlinkDetector(0.0)


def test_is_spontaneous_deliberate_closure_returns_false() -> None:
    assert blink_of(BlinkKind.COMPLETE).is_spontaneous
    assert not blink_of(BlinkKind.DELIBERATE).is_spontaneous
```

- [ ] **Step 3: Run to see them fail**

Run: `uv run pytest tests/unit/test_blink_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.analysis'`.

- [ ] **Step 4: Implement**

`src/spare_my_eyes/analysis/__init__.py`: empty.

`src/spare_my_eyes/analysis/blink_detector.py`:

```python
from dataclasses import dataclass
from enum import StrEnum

from spare_my_eyes.capture.face_sample import FaceSample


class BlinkKind(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    DELIBERATE = "deliberate"


@dataclass(frozen=True, slots=True)
class Blink:
    ended_at: float
    duration_seconds: float
    min_ear_ratio: float
    kind: BlinkKind

    @property
    def is_spontaneous(self) -> bool:
        return self.kind is not BlinkKind.DELIBERATE


@dataclass(frozen=True, slots=True)
class BlinkThresholds:
    closing_ratio: float = 0.8
    complete_ratio: float = 0.4
    max_spontaneous_seconds: float = 0.5


DEFAULT_BLINK_THRESHOLDS = BlinkThresholds()


class BlinkDetector:
    def __init__(
        self, open_ear_baseline: float, thresholds: BlinkThresholds = DEFAULT_BLINK_THRESHOLDS
    ) -> None:
        if open_ear_baseline <= 0:
            raise ValueError(f"open_ear_baseline must be > 0, got {open_ear_baseline}")
        self._baseline = open_ear_baseline
        self._thresholds = thresholds
        self._closed_since: float | None = None
        self._min_ratio = 1.0

    def update(self, sample: FaceSample) -> Blink | None:
        if not sample.face_present:
            self.reset()
            return None
        ratio = sample.mean_ear / self._baseline
        if ratio < self._thresholds.closing_ratio:
            self._track_closure(sample.timestamp, ratio)
            return None
        return self._finish_closure(sample.timestamp)

    def reset(self) -> None:
        self._closed_since = None

    def _track_closure(self, timestamp: float, ratio: float) -> None:
        if self._closed_since is None:
            self._closed_since = timestamp
            self._min_ratio = ratio
            return
        self._min_ratio = min(self._min_ratio, ratio)

    def _finish_closure(self, timestamp: float) -> Blink | None:
        if self._closed_since is None:
            return None
        duration = timestamp - self._closed_since
        self._closed_since = None
        return Blink(timestamp, duration, self._min_ratio, self._classify(duration))

    def _classify(self, duration: float) -> BlinkKind:
        if duration > self._thresholds.max_spontaneous_seconds:
            return BlinkKind.DELIBERATE
        if self._min_ratio < self._thresholds.complete_ratio:
            return BlinkKind.COMPLETE
        return BlinkKind.INCOMPLETE
```

- [ ] **Step 5: Run to see them pass**

Run: `uv run pytest tests/unit/test_blink_detector.py -v && uv run mypy`
Expected: 8 passed, mypy clean.

- [ ] **Step 6: Commit**

```bash
git add src/spare_my_eyes/analysis tests/fakes/samples.py tests/unit/test_blink_detector.py
git commit -m "feat: detect complete, incomplete and deliberate blinks from EAR

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: BlinkRateMonitor

**Files:**
- Create: `src/spare_my_eyes/analysis/blink_rate.py`
- Test: `tests/unit/test_blink_rate.py`

**Interfaces:**
- Consumes: `FaceSample`, `Blink`, `BlinkKind` (Tasks 2, 4).
- Produces:
  - `BlinkStats(blinks_per_minute: float, incomplete_ratio: float, covered_seconds: float, window_full: bool)`, frozen.
  - `BlinkRateMonitor(window_seconds: float = 120.0)` with `observe(sample) -> None`, `record(blink) -> None`, `stats() -> BlinkStats | None`, `reset() -> None`.

The window is measured in *presence time*: seconds with a face in view. Absence freezes it. A gap between two present samples counts as at most 1 s, so a sleeping PC never inflates it.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_blink_rate.py`:

```python
import pytest

from spare_my_eyes.analysis.blink_detector import BlinkKind
from spare_my_eyes.analysis.blink_rate import BlinkRateMonitor
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import blink_of, samples_from_ears

FPS = 20.0


def present_from(monitor: BlinkRateMonitor, start: float, end: float) -> None:
    count = round((end - start) * FPS) + 1
    for sample in samples_from_ears([0.3] * count, fps=FPS, start=start):
        monitor.observe(sample)


def record_many(monitor: BlinkRateMonitor, kind: BlinkKind, count: int) -> None:
    for _ in range(count):
        monitor.record(blink_of(kind))


def test_stats_before_any_presence_returns_none() -> None:
    assert BlinkRateMonitor().stats() is None


def test_stats_ten_blinks_over_full_window_reports_five_per_minute() -> None:
    monitor = BlinkRateMonitor(window_seconds=120.0)
    for index in range(10):
        present_from(monitor, index * 12.0, index * 12.0 + 11.95)
        monitor.record(blink_of(BlinkKind.COMPLETE))
    present_from(monitor, 120.0, 120.0)
    stats = monitor.stats()
    assert stats is not None
    assert stats.blinks_per_minute == pytest.approx(5.0, abs=0.05)
    assert stats.window_full


def test_stats_partial_window_reports_rate_over_covered_time() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 30.0)
    record_many(monitor, BlinkKind.COMPLETE, 3)
    stats = monitor.stats()
    assert stats is not None
    assert stats.blinks_per_minute == pytest.approx(6.0)
    assert stats.covered_seconds == pytest.approx(30.0)
    assert not stats.window_full


def test_stats_blinks_older_than_window_are_dropped() -> None:
    monitor = BlinkRateMonitor(window_seconds=120.0)
    present_from(monitor, 0.0, 10.0)
    record_many(monitor, BlinkKind.COMPLETE, 6)
    present_from(monitor, 10.05, 140.0)
    stats = monitor.stats()
    assert stats is not None
    assert stats.blinks_per_minute == pytest.approx(0.0)


def test_observe_absence_does_not_advance_window() -> None:
    monitor = BlinkRateMonitor(window_seconds=120.0)
    present_from(monitor, 0.0, 60.0)
    record_many(monitor, BlinkKind.COMPLETE, 4)
    for step in range(1, 100):
        monitor.observe(FaceSample.absent(60.0 + step * 3.0))
    present_from(monitor, 400.0, 460.0)
    stats = monitor.stats()
    assert stats is not None
    assert stats.window_full
    assert stats.blinks_per_minute == pytest.approx(2.0)


def test_stats_incomplete_blinks_report_their_ratio() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 120.0)
    record_many(monitor, BlinkKind.COMPLETE, 3)
    record_many(monitor, BlinkKind.INCOMPLETE, 1)
    stats = monitor.stats()
    assert stats is not None
    assert stats.incomplete_ratio == pytest.approx(0.25)


def test_record_deliberate_closure_is_ignored() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 120.0)
    record_many(monitor, BlinkKind.DELIBERATE, 5)
    stats = monitor.stats()
    assert stats is not None
    assert stats.blinks_per_minute == pytest.approx(0.0)


def test_observe_long_gap_between_samples_counts_at_most_one_second() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 0.0)
    present_from(monitor, 3600.0, 3600.0)
    stats = monitor.stats()
    assert stats is not None
    assert stats.covered_seconds == pytest.approx(1.0)


def test_reset_clears_presence_and_blinks() -> None:
    monitor = BlinkRateMonitor()
    present_from(monitor, 0.0, 30.0)
    record_many(monitor, BlinkKind.COMPLETE, 3)
    monitor.reset()
    assert monitor.stats() is None
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_blink_rate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.analysis.blink_rate'`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/analysis/blink_rate.py`:

```python
from collections import deque
from dataclasses import dataclass

from spare_my_eyes.analysis.blink_detector import Blink, BlinkKind
from spare_my_eyes.capture.face_sample import FaceSample

_TOLERANCE_SECONDS = 1e-6


@dataclass(frozen=True, slots=True)
class BlinkStats:
    blinks_per_minute: float
    incomplete_ratio: float
    covered_seconds: float
    window_full: bool


class BlinkRateMonitor:
    MAX_SAMPLE_GAP_SECONDS = 1.0

    def __init__(self, window_seconds: float = 120.0) -> None:
        self._window = window_seconds
        self._presence_seconds = 0.0
        self._last_present_at: float | None = None
        self._blinks: deque[tuple[float, BlinkKind]] = deque()

    def observe(self, sample: FaceSample) -> None:
        if not sample.face_present:
            self._last_present_at = None
            return
        if self._last_present_at is not None:
            gap = sample.timestamp - self._last_present_at
            self._presence_seconds += min(max(gap, 0.0), self.MAX_SAMPLE_GAP_SECONDS)
        self._last_present_at = sample.timestamp
        self._drop_expired()

    def record(self, blink: Blink) -> None:
        if blink.is_spontaneous:
            self._blinks.append((self._presence_seconds, blink.kind))

    def stats(self) -> BlinkStats | None:
        covered = min(self._presence_seconds, self._window)
        if covered <= 0:
            return None
        count = len(self._blinks)
        incomplete = sum(1 for _, kind in self._blinks if kind is BlinkKind.INCOMPLETE)
        return BlinkStats(
            blinks_per_minute=count * 60.0 / covered,
            incomplete_ratio=incomplete / count if count else 0.0,
            covered_seconds=covered,
            window_full=covered >= self._window - _TOLERANCE_SECONDS,
        )

    def reset(self) -> None:
        self._presence_seconds = 0.0
        self._last_present_at = None
        self._blinks.clear()

    def _drop_expired(self) -> None:
        oldest_allowed = self._presence_seconds - self._window
        while self._blinks and self._blinks[0][0] < oldest_allowed:
            self._blinks.popleft()
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit/test_blink_rate.py -v && uv run mypy`
Expected: 9 passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/analysis/blink_rate.py tests/unit/test_blink_rate.py
git commit -m "feat: measure blink rate over a sliding window of presence time

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: ScreenDistanceEstimator

**Files:**
- Create: `src/spare_my_eyes/analysis/distance.py`
- Test: `tests/unit/test_distance.py`

**Interfaces:**
- Consumes: `FaceSample`.
- Produces:
  - `ARM_LENGTH_CM = 60.0`; `focal_scale_from_calibration(iris_diameter_px_at_arm_length: float) -> float` (= iris px × 60).
  - `DistanceThresholds(too_close_cm=50.0, clear_cm=55.0, hold_seconds=30.0)`, frozen.
  - `DistanceReading(distance_cm: float, too_close: bool)`, frozen.
  - `ScreenDistanceEstimator(focal_scale: float, thresholds: DistanceThresholds = DistanceThresholds())` with `update(sample) -> DistanceReading | None` (None when no face or no iris) and `reset() -> None`.

Distance is `focal_scale / median(last 10 iris diameters)`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_distance.py`:

```python
import pytest

from spare_my_eyes.analysis.distance import (
    DistanceReading,
    ScreenDistanceEstimator,
    focal_scale_from_calibration,
)
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import samples_from_ears

FOCAL_SCALE = 660.0
FPS = 20.0


def at_distance(
    estimator: ScreenDistanceEstimator, centimeters: float, start: float, end: float
) -> DistanceReading | None:
    count = round((end - start) * FPS) + 1
    iris = FOCAL_SCALE / centimeters
    reading = None
    for sample in samples_from_ears([0.3] * count, fps=FPS, start=start, iris_diameter_px=iris):
        reading = estimator.update(sample)
    return reading


def test_focal_scale_from_calibration_arm_length_iris_returns_scale() -> None:
    assert focal_scale_from_calibration(11.0) == pytest.approx(660.0)


def test_update_far_face_reports_distance_and_not_too_close() -> None:
    reading = at_distance(ScreenDistanceEstimator(FOCAL_SCALE), 60.0, 0.0, 0.0)
    assert reading is not None
    assert reading.distance_cm == pytest.approx(60.0)
    assert not reading.too_close


def test_update_close_for_less_than_hold_is_not_too_close() -> None:
    reading = at_distance(ScreenDistanceEstimator(FOCAL_SCALE), 45.0, 0.0, 29.9)
    assert reading is not None and not reading.too_close


def test_update_close_for_hold_seconds_reports_too_close() -> None:
    reading = at_distance(ScreenDistanceEstimator(FOCAL_SCALE), 45.0, 0.0, 30.0)
    assert reading is not None and reading.too_close


def test_update_between_thresholds_after_too_close_stays_too_close() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 45.0, 0.0, 30.0)
    reading = at_distance(estimator, 52.0, 30.05, 35.0)
    assert reading is not None and reading.too_close


def test_update_beyond_clear_distance_clears_too_close() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 45.0, 0.0, 30.0)
    reading = at_distance(estimator, 58.0, 30.05, 35.0)
    assert reading is not None and not reading.too_close


def test_update_brief_move_back_restarts_hold() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 45.0, 0.0, 20.0)
    at_distance(estimator, 60.0, 20.05, 21.0)
    reading = at_distance(estimator, 45.0, 21.05, 45.0)
    assert reading is not None and not reading.too_close


def test_update_single_outlier_is_smoothed_by_median() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 60.0, 0.0, 5.0)
    outlier = samples_from_ears([0.3], start=5.05, iris_diameter_px=30.0)[0]
    reading = estimator.update(outlier)
    assert reading is not None
    assert reading.distance_cm == pytest.approx(60.0, rel=0.01)


def test_update_absent_face_returns_none() -> None:
    assert ScreenDistanceEstimator(FOCAL_SCALE).update(FaceSample.absent(1.0)) is None


def test_reset_clears_too_close_state() -> None:
    estimator = ScreenDistanceEstimator(FOCAL_SCALE)
    at_distance(estimator, 45.0, 0.0, 30.0)
    estimator.reset()
    reading = at_distance(estimator, 45.0, 30.05, 30.05)
    assert reading is not None and not reading.too_close


def test_init_non_positive_focal_scale_raises_value_error() -> None:
    with pytest.raises(ValueError, match="focal_scale"):
        ScreenDistanceEstimator(0.0)
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_distance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.analysis.distance'`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/analysis/distance.py`:

```python
import statistics
from collections import deque
from dataclasses import dataclass

from spare_my_eyes.capture.face_sample import FaceSample

ARM_LENGTH_CM = 60.0


def focal_scale_from_calibration(iris_diameter_px_at_arm_length: float) -> float:
    return iris_diameter_px_at_arm_length * ARM_LENGTH_CM


@dataclass(frozen=True, slots=True)
class DistanceThresholds:
    too_close_cm: float = 50.0
    clear_cm: float = 55.0
    hold_seconds: float = 30.0


@dataclass(frozen=True, slots=True)
class DistanceReading:
    distance_cm: float
    too_close: bool


DEFAULT_DISTANCE_THRESHOLDS = DistanceThresholds()


class ScreenDistanceEstimator:
    SMOOTHING_SAMPLES = 10

    def __init__(
        self, focal_scale: float, thresholds: DistanceThresholds = DEFAULT_DISTANCE_THRESHOLDS
    ) -> None:
        if focal_scale <= 0:
            raise ValueError(f"focal_scale must be > 0, got {focal_scale}")
        self._focal_scale = focal_scale
        self._thresholds = thresholds
        self._recent: deque[float] = deque(maxlen=self.SMOOTHING_SAMPLES)
        self._close_since: float | None = None
        self._too_close = False

    def update(self, sample: FaceSample) -> DistanceReading | None:
        if not sample.face_present or sample.iris_diameter_px <= 0:
            return None
        self._recent.append(sample.iris_diameter_px)
        distance = self._focal_scale / statistics.median(self._recent)
        self._too_close = self._next_too_close(sample.timestamp, distance)
        return DistanceReading(distance_cm=distance, too_close=self._too_close)

    def reset(self) -> None:
        self._recent.clear()
        self._close_since = None
        self._too_close = False

    def _next_too_close(self, timestamp: float, distance: float) -> bool:
        if self._too_close:
            return self._still_too_close(distance)
        if distance >= self._thresholds.too_close_cm:
            self._close_since = None
            return False
        if self._close_since is None:
            self._close_since = timestamp
        return timestamp - self._close_since >= self._thresholds.hold_seconds

    def _still_too_close(self, distance: float) -> bool:
        if distance <= self._thresholds.clear_cm:
            return True
        self._close_since = None
        return False
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit/test_distance.py -v && uv run mypy`
Expected: 11 passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/analysis/distance.py tests/unit/test_distance.py
git commit -m "feat: estimate screen distance from iris size with hysteresis

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: WindowGazeDetector and PresenceTracker

**Files:**
- Create: `src/spare_my_eyes/analysis/gaze.py`, `src/spare_my_eyes/analysis/presence.py`
- Test: `tests/unit/test_gaze.py`, `tests/unit/test_presence.py`

**Interfaces:**
- Consumes: `FaceSample`.
- Produces:
  - `WindowSide` (StrEnum): `LEFT = "left"`, `RIGHT = "right"`.
  - `WindowGazeDetector(side: WindowSide, min_yaw_degrees: float = 25.0)` with `is_looking_at_window(sample) -> bool`. Negative yaw is the user's left.
  - `PresenceUpdate(present: bool, returned_after_seconds: float | None)`, frozen.
  - `PresenceTracker(absent_after_seconds: float = 60.0)` with `update(now: float, seen_at: float | None) -> PresenceUpdate`. `seen_at` is the latest moment the user was known to be there (face seen, or last keyboard/mouse input). `returned_after_seconds` is set only on the update where an absent user becomes present again; it holds the length of the gap.

"Was present" is judged at `now` against the previous sighting, not against stored state. A long silent gap with no updates (PC asleep) therefore still counts as an absence.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_gaze.py`:

```python
import pytest

from spare_my_eyes.analysis.gaze import WindowGazeDetector, WindowSide
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import samples_from_ears


def turned(yaw: float) -> FaceSample:
    return samples_from_ears([0.3], head_yaw_degrees=yaw)[0]


@pytest.mark.parametrize(
    ("yaw", "expected"), [(-30.0, True), (-25.0, True), (-20.0, False), (30.0, False)]
)
def test_is_looking_at_window_left_side_requires_left_turn(yaw: float, expected: bool) -> None:
    assert WindowGazeDetector(WindowSide.LEFT).is_looking_at_window(turned(yaw)) is expected


@pytest.mark.parametrize(("yaw", "expected"), [(30.0, True), (20.0, False), (-30.0, False)])
def test_is_looking_at_window_right_side_requires_right_turn(yaw: float, expected: bool) -> None:
    assert WindowGazeDetector(WindowSide.RIGHT).is_looking_at_window(turned(yaw)) is expected


def test_is_looking_at_window_no_face_returns_false() -> None:
    assert not WindowGazeDetector(WindowSide.LEFT).is_looking_at_window(FaceSample.absent(0.0))
```

`tests/unit/test_presence.py`:

```python
from spare_my_eyes.analysis.presence import PresenceTracker, PresenceUpdate


def test_update_first_sighting_is_present_without_return() -> None:
    assert PresenceTracker().update(0.0, 0.0) == PresenceUpdate(True, None)


def test_update_never_seen_is_absent() -> None:
    assert PresenceTracker().update(10.0, None) == PresenceUpdate(False, None)


def test_update_short_gap_stays_present() -> None:
    tracker = PresenceTracker(absent_after_seconds=60.0)
    tracker.update(0.0, 0.0)
    assert tracker.update(59.0, None) == PresenceUpdate(True, None)


def test_update_no_sighting_for_absent_after_is_absent() -> None:
    tracker = PresenceTracker(absent_after_seconds=60.0)
    tracker.update(0.0, 0.0)
    assert tracker.update(60.0, None) == PresenceUpdate(False, None)


def test_update_return_after_absence_reports_absence_duration() -> None:
    tracker = PresenceTracker()
    tracker.update(0.0, 0.0)
    tracker.update(100.0, None)
    assert tracker.update(400.0, 400.0) == PresenceUpdate(True, 400.0)


def test_update_sighting_after_long_silent_gap_reports_absence() -> None:
    tracker = PresenceTracker()
    tracker.update(0.0, 0.0)
    assert tracker.update(3600.0, 3600.0) == PresenceUpdate(True, 3600.0)


def test_update_older_sighting_does_not_move_last_seen_back() -> None:
    tracker = PresenceTracker()
    tracker.update(10.0, 10.0)
    tracker.update(20.0, 5.0)
    assert tracker.update(69.0, None).present


def test_update_stale_sighting_while_absent_does_not_report_return() -> None:
    tracker = PresenceTracker()
    tracker.update(0.0, 0.0)
    assert tracker.update(500.0, 100.0) == PresenceUpdate(False, None)
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_gaze.py tests/unit/test_presence.py -v`
Expected: FAIL with `ModuleNotFoundError` for `spare_my_eyes.analysis.gaze` and `spare_my_eyes.analysis.presence`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/analysis/gaze.py`:

```python
from enum import StrEnum

from spare_my_eyes.capture.face_sample import FaceSample


class WindowSide(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class WindowGazeDetector:
    def __init__(self, side: WindowSide, min_yaw_degrees: float = 25.0) -> None:
        self._side = side
        self._min_yaw = min_yaw_degrees

    def is_looking_at_window(self, sample: FaceSample) -> bool:
        if not sample.face_present:
            return False
        if self._side is WindowSide.LEFT:
            return sample.head_yaw_degrees <= -self._min_yaw
        return sample.head_yaw_degrees >= self._min_yaw
```

`src/spare_my_eyes/analysis/presence.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PresenceUpdate:
    present: bool
    returned_after_seconds: float | None


class PresenceTracker:
    def __init__(self, absent_after_seconds: float = 60.0) -> None:
        self._absent_after = absent_after_seconds
        self._last_seen: float | None = None

    def update(self, now: float, seen_at: float | None) -> PresenceUpdate:
        previous = self._last_seen
        was_present = self._seen_recently(previous, now)
        self._last_seen = _latest(previous, seen_at)
        present = self._seen_recently(self._last_seen, now)
        return PresenceUpdate(present, self._absence(previous, was_present, present))

    def _absence(self, previous: float | None, was_present: bool, present: bool) -> float | None:
        if was_present or not present or previous is None or self._last_seen is None:
            return None
        return self._last_seen - previous

    def _seen_recently(self, seen_at: float | None, now: float) -> bool:
        return seen_at is not None and now - seen_at < self._absent_after


def _latest(current: float | None, candidate: float | None) -> float | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return max(current, candidate)
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit/test_gaze.py tests/unit/test_presence.py -v && uv run mypy`
Expected: all passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/analysis/gaze.py src/spare_my_eyes/analysis/presence.py tests/unit/test_gaze.py tests/unit/test_presence.py
git commit -m "feat: detect gaze toward the window and track presence

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Structured logging, Settings and JsonSettingsStore

**Files:**
- Create: `src/spare_my_eyes/structured_log.py`, `src/spare_my_eyes/settings.py`, `src/spare_my_eyes/settings_store.py`
- Create: `tests/fakes/logs.py`, `tests/fakes/settings_store.py`, `tests/conftest.py`
- Test: `tests/unit/test_structured_log.py`, `tests/unit/test_settings.py`, `tests/unit/test_settings_store.py`

**Interfaces:**
- Consumes: `WindowSide` (Task 7).
- Produces:
  - `log_event(logger: logging.Logger, level: int, event: str, **fields: object) -> None`; `JsonLogFormatter`; `configure_file_logging(log_dir: Path, logger_name: str = "spare_my_eyes") -> logging.Logger` (rotating `spare-my-eyes.log`, 1 MB × 3).
  - `Settings` (frozen dataclass, all fields below) with property `is_calibrated -> bool`.
  - `settings_from_overrides(overrides: Mapping[str, object], logger: logging.Logger) -> Settings`; `settings_to_overrides(settings: Settings) -> dict[str, object]`.
  - `SettingsStore` protocol: `load() -> Settings`, `save(settings: Settings) -> None`; `JsonSettingsStore(path: Path, logger: logging.Logger)`.
  - Fakes: `RecordingLogHandler` (`.logger`, `.records`, `events()`, `fields_of(event)`, classmethod `attached_to_new_logger(name)`); fixture `log_recorder`; `InMemorySettingsStore(settings: Settings | None = None)` with `.settings`, `.saved`.

Logged events: `settings_unknown_key` (key), `settings_invalid_value` (key, value, reason), `settings_file_corrupt` (path, content truncated to 2000 chars).

- [ ] **Step 1: Write the test doubles**

`tests/fakes/logs.py`:

```python
import logging
from typing import Self


class RecordingLogHandler(logging.Handler):
    def __init__(self, logger: logging.Logger) -> None:
        super().__init__(level=logging.DEBUG)
        self.logger = logger
        self.records: list[logging.LogRecord] = []

    @classmethod
    def attached_to_new_logger(cls, name: str) -> Self:
        logger = logging.getLogger(f"tests.{name}")
        logger.handlers.clear()
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        handler = cls(logger)
        logger.addHandler(handler)
        return handler

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def events(self) -> list[str]:
        return [record.getMessage() for record in self.records]

    def fields_of(self, event: str) -> dict[str, object]:
        for record in self.records:
            if record.getMessage() == event:
                fields = getattr(record, "fields", {})
                return dict(fields) if isinstance(fields, dict) else {}
        raise AssertionError(f"No log record with event {event!r}; recorded {self.events()!r}")
```

`tests/fakes/settings_store.py`:

```python
from spare_my_eyes.settings import Settings


class InMemorySettingsStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else Settings()
        self.saved: list[Settings] = []

    def load(self) -> Settings:
        return self.settings

    def save(self, settings: Settings) -> None:
        self.settings = settings
        self.saved.append(settings)
```

`tests/conftest.py`:

```python
import pytest

from tests.fakes.logs import RecordingLogHandler


@pytest.fixture
def log_recorder(request: pytest.FixtureRequest) -> RecordingLogHandler:
    return RecordingLogHandler.attached_to_new_logger(request.node.name)
```

- [ ] **Step 2: Write the failing tests**

`tests/unit/test_structured_log.py`:

```python
import json
import logging
from pathlib import Path

from spare_my_eyes.structured_log import JsonLogFormatter, configure_file_logging, log_event
from tests.fakes.logs import RecordingLogHandler


def test_format_event_with_fields_produces_json_line(log_recorder: RecordingLogHandler) -> None:
    log_event(log_recorder.logger, logging.WARNING, "settings_file_corrupt", path="C:/x.json")
    entry = json.loads(JsonLogFormatter().format(log_recorder.records[0]))
    assert entry["event"] == "settings_file_corrupt"
    assert entry["level"] == "WARNING"
    assert entry["path"] == "C:/x.json"
    assert "time" in entry


def test_format_exception_includes_traceback(log_recorder: RecordingLogHandler) -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        log_recorder.logger.exception("capture_thread_crashed")
    entry = json.loads(JsonLogFormatter().format(log_recorder.records[0]))
    assert "RuntimeError: boom" in entry["exception"]


def test_configure_file_logging_writes_json_lines_to_log_dir(tmp_path: Path) -> None:
    logger = configure_file_logging(tmp_path / "logs", logger_name="tests.configure_file_logging")
    log_event(logger, logging.INFO, "app_started", scripted_camera=None)
    for handler in logger.handlers:
        handler.close()
    line = (tmp_path / "logs" / "spare-my-eyes.log").read_text(encoding="utf-8").splitlines()[0]
    assert json.loads(line)["event"] == "app_started"
```

`tests/unit/test_settings.py`:

```python
from dataclasses import replace

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.settings import Settings, settings_from_overrides, settings_to_overrides
from tests.fakes.logs import RecordingLogHandler


def test_settings_defaults_match_spec() -> None:
    settings = Settings()
    assert settings.window_side is WindowSide.LEFT
    assert settings.frames_per_second == 20.0
    assert settings.blink_rate_threshold_per_minute == 8.0
    assert settings.too_close_cm == 50.0
    assert settings.break_interval_seconds == 1200.0
    assert not settings.is_calibrated


def test_settings_from_overrides_valid_values_replace_defaults(
    log_recorder: RecordingLogHandler,
) -> None:
    overrides = {"window_side": "right", "break_interval_seconds": 600, "break_slow_blinks": 3}
    settings = settings_from_overrides(overrides, log_recorder.logger)
    assert settings.window_side is WindowSide.RIGHT
    assert settings.break_interval_seconds == 600.0
    assert settings.break_slow_blinks == 3
    assert log_recorder.records == []


def test_settings_from_overrides_unknown_key_is_logged_and_ignored(
    log_recorder: RecordingLogHandler,
) -> None:
    settings = settings_from_overrides({"brightness": 3}, log_recorder.logger)
    assert settings == Settings()
    assert log_recorder.fields_of("settings_unknown_key") == {"key": "brightness"}


def test_settings_from_overrides_wrong_type_keeps_default_and_logs(
    log_recorder: RecordingLogHandler,
) -> None:
    overrides = {"frames_per_second": "fast", "snooze_seconds": 120}
    settings = settings_from_overrides(overrides, log_recorder.logger)
    assert settings.frames_per_second == 20.0
    assert settings.snooze_seconds == 120.0
    fields = log_recorder.fields_of("settings_invalid_value")
    assert fields["key"] == "frames_per_second"
    assert fields["value"] == "'fast'"


def test_settings_from_overrides_negative_number_keeps_default(
    log_recorder: RecordingLogHandler,
) -> None:
    assert settings_from_overrides({"too_close_cm": -5}, log_recorder.logger).too_close_cm == 50.0


def test_settings_from_overrides_boolean_for_number_keeps_default(
    log_recorder: RecordingLogHandler,
) -> None:
    settings = settings_from_overrides({"snooze_seconds": True}, log_recorder.logger)
    assert settings.snooze_seconds == 300.0


def test_settings_from_overrides_invalid_window_side_keeps_default(
    log_recorder: RecordingLogHandler,
) -> None:
    settings = settings_from_overrides({"window_side": "up"}, log_recorder.logger)
    assert settings.window_side is WindowSide.LEFT


def test_settings_to_overrides_defaults_returns_empty_dict() -> None:
    assert settings_to_overrides(Settings()) == {}


def test_settings_to_overrides_changed_values_returns_only_changes() -> None:
    settings = replace(Settings(), window_side=WindowSide.RIGHT, open_ear_baseline=0.3)
    assert settings_to_overrides(settings) == {"window_side": "right", "open_ear_baseline": 0.3}


def test_is_calibrated_both_values_set_returns_true() -> None:
    assert replace(Settings(), open_ear_baseline=0.3, focal_scale=660.0).is_calibrated
```

`tests/unit/test_settings_store.py`:

```python
import json
from dataclasses import replace
from pathlib import Path

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.settings import Settings
from spare_my_eyes.settings_store import JsonSettingsStore
from tests.fakes.logs import RecordingLogHandler


def test_load_missing_file_returns_defaults(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    store = JsonSettingsStore(tmp_path / "settings.json", log_recorder.logger)
    assert store.load() == Settings()


def test_save_then_load_round_trips_and_writes_only_overrides(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path, log_recorder.logger)
    settings = replace(Settings(), window_side=WindowSide.RIGHT, focal_scale=660.0)
    store.save(settings)
    assert store.load() == settings
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "window_side": "right",
        "focal_scale": 660.0,
    }


def test_save_missing_parent_directory_creates_it(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "SpareMyEyes" / "settings.json"
    JsonSettingsStore(path, log_recorder.logger).save(Settings())
    assert path.is_file()


def test_load_invalid_json_logs_content_and_returns_defaults_without_overwriting(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert JsonSettingsStore(path, log_recorder.logger).load() == Settings()
    assert path.read_text(encoding="utf-8") == "{not json"
    assert log_recorder.fields_of("settings_file_corrupt")["content"] == "{not json"


def test_load_json_array_is_treated_as_corrupt(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    path.write_text("[1, 2]", encoding="utf-8")
    assert JsonSettingsStore(path, log_recorder.logger).load() == Settings()
    assert "settings_file_corrupt" in log_recorder.events()
```

- [ ] **Step 3: Run to see them fail**

Run: `uv run pytest tests/unit/test_structured_log.py tests/unit/test_settings.py tests/unit/test_settings_store.py -v`
Expected: FAIL with `ModuleNotFoundError` for `spare_my_eyes.structured_log`, `spare_my_eyes.settings`, `spare_my_eyes.settings_store`.

- [ ] **Step 4: Implement structured logging**

`src/spare_my_eyes/structured_log.py`:

```python
import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE_NAME = "spare-my-eyes.log"


def log_event(logger: logging.Logger, level: int, event: str, **fields: object) -> None:
    logger.log(level, event, extra={"fields": fields})


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            entry.update(fields)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_file_logging(log_dir: Path, logger_name: str = "spare_my_eyes") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger
```

- [ ] **Step 5: Implement Settings**

`src/spare_my_eyes/settings.py`:

```python
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, replace
from typing import Any

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.structured_log import log_event


@dataclass(frozen=True, slots=True)
class Settings:
    window_side: WindowSide = WindowSide.LEFT
    camera_index: int = 0
    frames_per_second: float = 20.0
    blink_rate_threshold_per_minute: float = 8.0
    incomplete_ratio_threshold: float = 0.3
    blink_window_seconds: float = 120.0
    nudge_max_seconds: float = 8.0
    nudge_cooldown_seconds: float = 180.0
    nudge_hide_after_complete_blinks: int = 2
    too_close_cm: float = 50.0
    distance_clear_cm: float = 55.0
    distance_hold_seconds: float = 30.0
    distance_cooldown_seconds: float = 300.0
    break_interval_seconds: float = 1200.0
    break_gaze_seconds: float = 20.0
    break_min_yaw_degrees: float = 25.0
    break_slow_blinks: int = 5
    slow_blink_min_seconds: float = 0.3
    break_inactivity_timeout_seconds: float = 120.0
    snooze_seconds: float = 300.0
    absent_after_seconds: float = 60.0
    absence_reset_seconds: float = 300.0
    camera_retry_seconds: float = 60.0
    open_ear_baseline: float | None = None
    focal_scale: float | None = None

    @property
    def is_calibrated(self) -> bool:
        return self.open_ear_baseline is not None and self.focal_scale is not None


def settings_from_overrides(overrides: Mapping[str, object], logger: logging.Logger) -> Settings:
    accepted: dict[str, Any] = {}
    for key, value in overrides.items():
        parsed = _parse_override(key, value, logger)
        if parsed is not None:
            accepted[key] = parsed
    return replace(Settings(), **accepted)


def settings_to_overrides(settings: Settings) -> dict[str, object]:
    defaults = Settings()
    return {
        field.name: getattr(settings, field.name)
        for field in fields(Settings)
        if getattr(settings, field.name) != getattr(defaults, field.name)
    }


def _parse_override(key: str, value: object, logger: logging.Logger) -> object | None:
    parser = _PARSERS.get(key)
    if parser is None:
        log_event(logger, logging.WARNING, "settings_unknown_key", key=key)
        return None
    try:
        return parser(value)
    except ValueError as error:
        log_event(
            logger,
            logging.WARNING,
            "settings_invalid_value",
            key=key,
            value=repr(value),
            reason=str(error),
        )
        return None


def _positive_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise ValueError(f"expected a positive number, got {value!r}")
    return float(value)


def _optional_positive_float(value: object) -> float | None:
    return None if value is None else _positive_float(value)


def _positive_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"expected a positive integer, got {value!r}")
    return value


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"expected an integer >= 0, got {value!r}")
    return value


def _window_side(value: object) -> WindowSide:
    if not isinstance(value, str) or value not in {side.value for side in WindowSide}:
        raise ValueError(f"expected 'left' or 'right', got {value!r}")
    return WindowSide(value)


_FLOAT_FIELDS = (
    "frames_per_second",
    "blink_rate_threshold_per_minute",
    "incomplete_ratio_threshold",
    "blink_window_seconds",
    "nudge_max_seconds",
    "nudge_cooldown_seconds",
    "too_close_cm",
    "distance_clear_cm",
    "distance_hold_seconds",
    "distance_cooldown_seconds",
    "break_interval_seconds",
    "break_gaze_seconds",
    "break_min_yaw_degrees",
    "slow_blink_min_seconds",
    "break_inactivity_timeout_seconds",
    "snooze_seconds",
    "absent_after_seconds",
    "absence_reset_seconds",
    "camera_retry_seconds",
)

_PARSERS: dict[str, Callable[[object], object]] = {
    "window_side": _window_side,
    "camera_index": _non_negative_int,
    "nudge_hide_after_complete_blinks": _positive_int,
    "break_slow_blinks": _positive_int,
    "open_ear_baseline": _optional_positive_float,
    "focal_scale": _optional_positive_float,
    **{name: _positive_float for name in _FLOAT_FIELDS},
}
```

- [ ] **Step 6: Implement JsonSettingsStore**

`src/spare_my_eyes/settings_store.py`:

```python
import json
import logging
import os
from pathlib import Path
from typing import Protocol

from spare_my_eyes.settings import Settings, settings_from_overrides, settings_to_overrides
from spare_my_eyes.structured_log import log_event

_MAX_LOGGED_CONTENT = 2000


class SettingsStore(Protocol):
    def load(self) -> Settings: ...

    def save(self, settings: Settings) -> None: ...


class JsonSettingsStore:
    def __init__(self, path: Path, logger: logging.Logger) -> None:
        self._path = path
        self._logger = logger

    def load(self) -> Settings:
        if not self._path.exists():
            return Settings()
        text = self._path.read_text(encoding="utf-8", errors="replace")
        overrides = self._parse(text)
        if overrides is None:
            return Settings()
        return settings_from_overrides(overrides, self._logger)

    def save(self, settings: Settings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".json.tmp")
        content = json.dumps(settings_to_overrides(settings), indent=2) + "\n"
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, self._path)

    def _parse(self, text: str) -> dict[str, object] | None:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
        log_event(
            self._logger,
            logging.WARNING,
            "settings_file_corrupt",
            path=str(self._path),
            content=text[:_MAX_LOGGED_CONTENT],
        )
        return None
```

- [ ] **Step 7: Run to see them pass**

Run: `uv run ruff format . && uv run pytest tests/unit -v && uv run mypy && uv run ruff check .`
Expected: all passed; mypy and ruff clean.

- [ ] **Step 8: Commit**

```bash
git add src/spare_my_eyes/structured_log.py src/spare_my_eyes/settings.py src/spare_my_eyes/settings_store.py tests/conftest.py tests/fakes/logs.py tests/fakes/settings_store.py tests/unit/test_structured_log.py tests/unit/test_settings.py tests/unit/test_settings_store.py
git commit -m "feat: add JSON logging and override-only settings store

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: CalibrationSession

**Files:**
- Create: `src/spare_my_eyes/calibration.py`
- Test: `tests/unit/test_calibration.py`

**Interfaces:**
- Consumes: `FaceSample`, `focal_scale_from_calibration` (Task 6).
- Produces:
  - `CalibrationStep` (StrEnum): `LOOK_AT_SCREEN`, `ARM_LENGTH`, `DONE`.
  - `CalibrationProgress(step: CalibrationStep, seconds_left: float)`, frozen.
  - `CalibrationResult(open_ear_baseline: float, focal_scale: float)`, frozen.
  - `CalibrationSession(started_at: float)` with `update(sample) -> CalibrationProgress`, `progress(now: float) -> CalibrationProgress`, property `result -> CalibrationResult | None`.

Each step lasts 10 s. A step with fewer than 30 face samples restarts. Step 1 stores the median EAR; step 2 stores the median iris diameter and converts it to a focal scale.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_calibration.py`:

```python
from collections.abc import Iterable

import pytest

from spare_my_eyes.calibration import (
    CalibrationProgress,
    CalibrationResult,
    CalibrationSession,
    CalibrationStep,
)
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import samples_from_ears


def feed(session: CalibrationSession, samples: Iterable[FaceSample]) -> CalibrationProgress:
    progress = session.progress(0.0)
    for sample in samples:
        progress = session.update(sample)
    return progress


def test_update_twenty_seconds_of_face_produces_result() -> None:
    session = CalibrationSession(started_at=0.0)
    progress = feed(session, samples_from_ears([0.30] * 401, iris_diameter_px=11.0))
    assert progress.step is CalibrationStep.DONE
    assert session.result == CalibrationResult(open_ear_baseline=0.30, focal_scale=660.0)


def test_update_blinks_during_first_step_do_not_move_baseline() -> None:
    session = CalibrationSession(started_at=0.0)
    ears = ([0.30] * 9 + [0.05]) * 40 + [0.30]
    feed(session, samples_from_ears(ears))
    assert session.result is not None
    assert session.result.open_ear_baseline == pytest.approx(0.30)


def test_update_after_first_step_reports_arm_length_step() -> None:
    session = CalibrationSession(started_at=0.0)
    progress = feed(session, samples_from_ears([0.30] * 202))
    assert progress.step is CalibrationStep.ARM_LENGTH


def test_update_without_face_restarts_step() -> None:
    session = CalibrationSession(started_at=0.0)
    feed(session, [FaceSample.absent(index / 20.0) for index in range(201)])
    progress = feed(session, samples_from_ears([0.30] * 199, start=10.05))
    assert progress.step is CalibrationStep.LOOK_AT_SCREEN
    assert session.result is None


def test_progress_mid_step_reports_seconds_left() -> None:
    session = CalibrationSession(started_at=0.0)
    progress = feed(session, samples_from_ears([0.30] * 81))
    assert progress.step is CalibrationStep.LOOK_AT_SCREEN
    assert progress.seconds_left == pytest.approx(6.0)
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_calibration.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.calibration'`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/calibration.py`:

```python
import statistics
from dataclasses import dataclass
from enum import StrEnum

from spare_my_eyes.analysis.distance import focal_scale_from_calibration
from spare_my_eyes.capture.face_sample import FaceSample


class CalibrationStep(StrEnum):
    LOOK_AT_SCREEN = "look_at_screen"
    ARM_LENGTH = "arm_length"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class CalibrationProgress:
    step: CalibrationStep
    seconds_left: float


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    open_ear_baseline: float
    focal_scale: float


class CalibrationSession:
    STEP_SECONDS = 10.0
    MIN_SAMPLES_PER_STEP = 30

    def __init__(self, started_at: float) -> None:
        self._step = CalibrationStep.LOOK_AT_SCREEN
        self._step_started_at = started_at
        self._values: list[float] = []
        self._open_ear_baseline = 0.0
        self._result: CalibrationResult | None = None

    @property
    def result(self) -> CalibrationResult | None:
        return self._result

    def update(self, sample: FaceSample) -> CalibrationProgress:
        if self._step is CalibrationStep.DONE:
            return self.progress(sample.timestamp)
        if sample.face_present:
            self._values.append(self._measure(sample))
        if sample.timestamp - self._step_started_at >= self.STEP_SECONDS:
            self._finish_step(sample.timestamp)
        return self.progress(sample.timestamp)

    def progress(self, now: float) -> CalibrationProgress:
        if self._step is CalibrationStep.DONE:
            return CalibrationProgress(self._step, 0.0)
        elapsed = now - self._step_started_at
        return CalibrationProgress(self._step, max(0.0, self.STEP_SECONDS - elapsed))

    def _measure(self, sample: FaceSample) -> float:
        if self._step is CalibrationStep.LOOK_AT_SCREEN:
            return sample.mean_ear
        return sample.iris_diameter_px

    def _finish_step(self, now: float) -> None:
        self._step_started_at = now
        values, self._values = self._values, []
        if len(values) < self.MIN_SAMPLES_PER_STEP:
            return
        self._advance(statistics.median(values))

    def _advance(self, median: float) -> None:
        if self._step is CalibrationStep.LOOK_AT_SCREEN:
            self._open_ear_baseline = median
            self._step = CalibrationStep.ARM_LENGTH
            return
        focal_scale = focal_scale_from_calibration(median)
        self._result = CalibrationResult(self._open_ear_baseline, focal_scale)
        self._step = CalibrationStep.DONE
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit/test_calibration.py -v && uv run mypy`
Expected: 5 passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/calibration.py tests/unit/test_calibration.py
git commit -m "feat: calibrate open-eye baseline and focal scale

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Cooldown and ScreenTimeCounter

**Files:**
- Create: `src/spare_my_eyes/coaching/__init__.py`, `src/spare_my_eyes/coaching/cooldown.py`, `src/spare_my_eyes/coaching/screen_time.py`
- Test: `tests/unit/test_cooldown.py`, `tests/unit/test_screen_time.py`

**Interfaces:**
- Produces:
  - `Cooldown(seconds: float)` with `is_ready(now) -> bool`, `start(now) -> None`, `clear() -> None`. Ready until first started.
  - `ScreenTimeCounter()` with `add_presence(now) -> None`, `pause() -> None`, `reset() -> None`, property `seconds -> float`. A gap between two `add_presence` calls counts as at most 2 s.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_cooldown.py`:

```python
from spare_my_eyes.coaching.cooldown import Cooldown


def test_is_ready_never_started_returns_true() -> None:
    assert Cooldown(180.0).is_ready(0.0)


def test_is_ready_within_cooldown_returns_false() -> None:
    cooldown = Cooldown(180.0)
    cooldown.start(10.0)
    assert not cooldown.is_ready(189.9)


def test_is_ready_after_cooldown_returns_true() -> None:
    cooldown = Cooldown(180.0)
    cooldown.start(10.0)
    assert cooldown.is_ready(190.0)


def test_clear_running_cooldown_makes_it_ready() -> None:
    cooldown = Cooldown(180.0)
    cooldown.start(10.0)
    cooldown.clear()
    assert cooldown.is_ready(11.0)
```

`tests/unit/test_screen_time.py`:

```python
import pytest

from spare_my_eyes.coaching.screen_time import ScreenTimeCounter


def add_every_second(counter: ScreenTimeCounter, start: int, end: int) -> None:
    for second in range(start, end + 1):
        counter.add_presence(float(second))


def test_add_presence_every_second_accumulates_elapsed_time() -> None:
    counter = ScreenTimeCounter()
    add_every_second(counter, 0, 10)
    assert counter.seconds == pytest.approx(10.0)


def test_pause_gap_after_pause_is_not_counted() -> None:
    counter = ScreenTimeCounter()
    add_every_second(counter, 0, 10)
    counter.pause()
    add_every_second(counter, 100, 105)
    assert counter.seconds == pytest.approx(15.0)


def test_add_presence_long_gap_counts_at_most_two_seconds() -> None:
    counter = ScreenTimeCounter()
    counter.add_presence(0.0)
    counter.add_presence(3600.0)
    assert counter.seconds == pytest.approx(2.0)


def test_reset_clears_accumulated_time() -> None:
    counter = ScreenTimeCounter()
    add_every_second(counter, 0, 10)
    counter.reset()
    counter.add_presence(11.0)
    assert counter.seconds == 0.0
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_cooldown.py tests/unit/test_screen_time.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.coaching'`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/coaching/__init__.py`: empty.

`src/spare_my_eyes/coaching/cooldown.py`:

```python
import math


class Cooldown:
    def __init__(self, seconds: float) -> None:
        self._seconds = seconds
        self._ready_at = -math.inf

    def is_ready(self, now: float) -> bool:
        return now >= self._ready_at

    def start(self, now: float) -> None:
        self._ready_at = now + self._seconds

    def clear(self) -> None:
        self._ready_at = -math.inf
```

`src/spare_my_eyes/coaching/screen_time.py`:

```python
class ScreenTimeCounter:
    MAX_GAP_SECONDS = 2.0

    def __init__(self) -> None:
        self._seconds = 0.0
        self._last_present_at: float | None = None

    @property
    def seconds(self) -> float:
        return self._seconds

    def add_presence(self, now: float) -> None:
        if self._last_present_at is not None:
            gap = now - self._last_present_at
            self._seconds += min(max(gap, 0.0), self.MAX_GAP_SECONDS)
        self._last_present_at = now

    def pause(self) -> None:
        self._last_present_at = None

    def reset(self) -> None:
        self._seconds = 0.0
        self._last_present_at = None
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit/test_cooldown.py tests/unit/test_screen_time.py -v && uv run mypy`
Expected: 8 passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/coaching tests/unit/test_cooldown.py tests/unit/test_screen_time.py
git commit -m "feat: add cooldown and screen-time counter

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: BreakSession

**Files:**
- Create: `src/spare_my_eyes/coaching/break_session.py`
- Test: `tests/unit/test_break_session.py`

**Interfaces:**
- Produces:
  - `BreakStep` (StrEnum): `LOOK_OUT`, `SLOW_BLINKS`. `BreakOutcome` (StrEnum): `COMPLETED`, `SKIPPED`, `TIMED_OUT`.
  - `BreakTargets(gaze_seconds=20.0, slow_blinks=5, slow_blink_min_seconds=0.3, slow_blink_ear_ratio=0.4, inactivity_timeout_seconds=120.0, unverified_blink_seconds=2.0)`, frozen.
  - `BreakProgress(step, gaze_seconds, gaze_target_seconds, slow_blinks, slow_blink_target, verified: bool)`, frozen.
  - `BreakSession` built with classmethods `verified_by_camera(started_at, targets)` and `on_honor_system(started_at, targets)`; methods `observe(timestamp: float, looking_at_window: bool, ear_ratio: float | None)`, `advance_unverified(now: float, user_is_idle: bool)`, `skip()`, `check_timeout(now: float)`, `progress() -> BreakProgress`; properties `outcome -> BreakOutcome | None`, `is_verified -> bool`.

An honor-system session (no camera) advances with time only while the user is idle at the keyboard and mouse. That is the closest signal to "looking away" without a camera.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_break_session.py`:

```python
import pytest

from spare_my_eyes.coaching.break_session import (
    BreakOutcome,
    BreakSession,
    BreakStep,
    BreakTargets,
)

FPS = 20.0
TARGETS = BreakTargets()


def observe_for(
    session: BreakSession, start: float, end: float, looking: bool, ear_ratio: float = 1.0
) -> None:
    for index in range(round((end - start) * FPS) + 1):
        session.observe(start + index / FPS, looking, ear_ratio)


def close_eyes(session: BreakSession, start: float, closed_seconds: float) -> None:
    for index in range(round(closed_seconds * FPS)):
        session.observe(start + index / FPS, False, 0.2)
    session.observe(start + closed_seconds, False, 1.0)


def session_on_blink_step() -> BreakSession:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 20.0, looking=True)
    return session


def test_progress_new_session_starts_looking_out() -> None:
    progress = BreakSession.verified_by_camera(0.0, TARGETS).progress()
    assert progress.step is BreakStep.LOOK_OUT
    assert progress.gaze_seconds == 0.0
    assert progress.verified


def test_observe_looking_at_window_for_target_moves_to_slow_blinks() -> None:
    progress = session_on_blink_step().progress()
    assert progress.step is BreakStep.SLOW_BLINKS
    assert progress.gaze_seconds == pytest.approx(20.0)


def test_observe_looking_away_does_not_advance_gaze() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 30.0, looking=False)
    assert session.progress().gaze_seconds == 0.0
    assert session.progress().step is BreakStep.LOOK_OUT


def test_observe_gaze_accumulates_across_interruptions() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 10.0, looking=True)
    observe_for(session, 10.05, 15.0, looking=False)
    observe_for(session, 15.05, 25.0, looking=True)
    assert session.progress().step is BreakStep.SLOW_BLINKS


def test_observe_five_slow_blinks_completes_break() -> None:
    session = session_on_blink_step()
    for index in range(5):
        close_eyes(session, 21.0 + index * 2.0, closed_seconds=0.4)
    assert session.outcome is BreakOutcome.COMPLETED


def test_observe_quick_blinks_do_not_count() -> None:
    session = session_on_blink_step()
    for index in range(5):
        close_eyes(session, 21.0 + index * 2.0, closed_seconds=0.15)
    assert session.progress().slow_blinks == 0
    assert session.outcome is None


def test_check_timeout_two_minutes_without_progress_times_out() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 120.0, looking=False)
    session.check_timeout(120.0)
    assert session.outcome is BreakOutcome.TIMED_OUT


def test_check_timeout_recent_progress_keeps_session_open() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 10.0, looking=True)
    session.check_timeout(125.0)
    assert session.outcome is None


def test_skip_open_session_records_skipped() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    session.skip()
    assert session.outcome is BreakOutcome.SKIPPED


def test_observe_after_outcome_is_ignored() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    session.skip()
    observe_for(session, 0.0, 20.0, looking=True)
    assert session.progress().gaze_seconds == 0.0


def test_advance_unverified_idle_user_progresses_by_time_and_completes() -> None:
    session = BreakSession.on_honor_system(0.0, TARGETS)
    for second in range(21):
        session.advance_unverified(float(second), user_is_idle=True)
    assert session.progress().step is BreakStep.SLOW_BLINKS
    assert not session.progress().verified
    for second in range(21, 31):
        session.advance_unverified(float(second), user_is_idle=True)
    assert session.outcome is BreakOutcome.COMPLETED


def test_advance_unverified_active_user_does_not_progress() -> None:
    session = BreakSession.on_honor_system(0.0, TARGETS)
    for second in range(30):
        session.advance_unverified(float(second), user_is_idle=False)
    assert session.progress().gaze_seconds == 0.0
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_break_session.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.coaching.break_session'`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/coaching/break_session.py`:

```python
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

_TOLERANCE = 1e-6


class BreakStep(StrEnum):
    LOOK_OUT = "look_out"
    SLOW_BLINKS = "slow_blinks"


class BreakOutcome(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True, slots=True)
class BreakTargets:
    gaze_seconds: float = 20.0
    slow_blinks: int = 5
    slow_blink_min_seconds: float = 0.3
    slow_blink_ear_ratio: float = 0.4
    inactivity_timeout_seconds: float = 120.0
    unverified_blink_seconds: float = 2.0


@dataclass(frozen=True, slots=True)
class BreakProgress:
    step: BreakStep
    gaze_seconds: float
    gaze_target_seconds: float
    slow_blinks: int
    slow_blink_target: int
    verified: bool


class BreakSession:
    """One combined break: look out the window, then a few slow, complete blinks."""

    MAX_SAMPLE_GAP_SECONDS = 1.0

    def __init__(self, started_at: float, targets: BreakTargets, *, verified: bool) -> None:
        self._targets = targets
        self._verified = verified
        self._step = BreakStep.LOOK_OUT
        self._outcome: BreakOutcome | None = None
        self._gaze_seconds = 0.0
        self._slow_blinks = 0
        self._paced_blink_seconds = 0.0
        self._closed_since: float | None = None
        self._last_timestamp: float | None = None
        self._last_activity_at = started_at

    @classmethod
    def verified_by_camera(cls, started_at: float, targets: BreakTargets) -> Self:
        return cls(started_at, targets, verified=True)

    @classmethod
    def on_honor_system(cls, started_at: float, targets: BreakTargets) -> Self:
        return cls(started_at, targets, verified=False)

    @property
    def outcome(self) -> BreakOutcome | None:
        return self._outcome

    @property
    def is_verified(self) -> bool:
        return self._verified

    def progress(self) -> BreakProgress:
        return BreakProgress(
            step=self._step,
            gaze_seconds=self._gaze_seconds,
            gaze_target_seconds=self._targets.gaze_seconds,
            slow_blinks=self._slow_blinks,
            slow_blink_target=self._targets.slow_blinks,
            verified=self._verified,
        )

    def observe(self, timestamp: float, looking_at_window: bool, ear_ratio: float | None) -> None:
        if self._outcome is not None:
            return
        elapsed = self._elapsed_until(timestamp)
        if self._step is BreakStep.LOOK_OUT:
            self._add_gaze(timestamp, elapsed if looking_at_window else 0.0)
            return
        self._track_slow_blink(timestamp, ear_ratio)

    def advance_unverified(self, now: float, user_is_idle: bool) -> None:
        if self._outcome is not None:
            return
        elapsed = self._elapsed_until(now)
        if not user_is_idle:
            return
        if self._step is BreakStep.LOOK_OUT:
            self._add_gaze(now, elapsed)
            return
        self._add_paced_blink_time(now, elapsed)

    def skip(self) -> None:
        if self._outcome is None:
            self._outcome = BreakOutcome.SKIPPED

    def check_timeout(self, now: float) -> None:
        if self._outcome is not None:
            return
        if now - self._last_activity_at >= self._targets.inactivity_timeout_seconds:
            self._outcome = BreakOutcome.TIMED_OUT

    def _elapsed_until(self, timestamp: float) -> float:
        previous, self._last_timestamp = self._last_timestamp, timestamp
        if previous is None:
            return 0.0
        return min(max(timestamp - previous, 0.0), self.MAX_SAMPLE_GAP_SECONDS)

    def _add_gaze(self, now: float, seconds: float) -> None:
        if seconds <= 0:
            return
        self._gaze_seconds = min(self._gaze_seconds + seconds, self._targets.gaze_seconds)
        self._last_activity_at = now
        if self._gaze_seconds >= self._targets.gaze_seconds - _TOLERANCE:
            self._gaze_seconds = self._targets.gaze_seconds
            self._step = BreakStep.SLOW_BLINKS

    def _track_slow_blink(self, timestamp: float, ear_ratio: float | None) -> None:
        if self._eyes_closed(ear_ratio):
            if self._closed_since is None:
                self._closed_since = timestamp
            return
        closed_since, self._closed_since = self._closed_since, None
        if closed_since is None:
            return
        if timestamp - closed_since >= self._targets.slow_blink_min_seconds - _TOLERANCE:
            self._count_slow_blink(timestamp)

    def _eyes_closed(self, ear_ratio: float | None) -> bool:
        return ear_ratio is not None and ear_ratio < self._targets.slow_blink_ear_ratio

    def _add_paced_blink_time(self, now: float, seconds: float) -> None:
        self._paced_blink_seconds += seconds
        if self._paced_blink_seconds < self._targets.unverified_blink_seconds - _TOLERANCE:
            return
        self._paced_blink_seconds = 0.0
        self._count_slow_blink(now)

    def _count_slow_blink(self, now: float) -> None:
        self._slow_blinks += 1
        self._last_activity_at = now
        if self._slow_blinks >= self._targets.slow_blinks:
            self._outcome = BreakOutcome.COMPLETED
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit/test_break_session.py -v && uv run mypy`
Expected: 12 passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/coaching/break_session.py tests/unit/test_break_session.py
git commit -m "feat: add verified and honor-system break session state machine

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Scripted face-sample timeline and the FaceSampleSource interface

**Files:**
- Create: `src/spare_my_eyes/capture/camera_errors.py`, `src/spare_my_eyes/capture/sample_source.py`, `src/spare_my_eyes/capture/scripted.py`, `src/spare_my_eyes/capture/scenarios.py`
- Create: `tests/fakes/sleeper.py`
- Test: `tests/unit/test_scripted.py`

**Interfaces:**
- Consumes: `FaceSample`, `Clock`; tests use `BlinkDetector` (Task 4).
- Produces:
  - `CameraUnavailableError(Exception)`, `CameraBusyError(Exception)` in `camera_errors.py`.
  - `CameraStatus` (StrEnum): `ACTIVE`, `UNAVAILABLE`, `BUSY`.
  - `FaceSampleSource` protocol: `open() -> None`, `next_sample() -> FaceSample`, `close() -> None` (close is idempotent). `open`/`next_sample` raise `CameraUnavailableError` or `CameraBusyError`.
  - `UnavailableSampleSource(reason: str)`: `open()` always raises `CameraUnavailableError(reason)`.
  - `OPEN_EAR = 0.30`, `DEFAULT_IRIS_DIAMETER_PX = 11.0`, `ScriptedBlink` (StrEnum `COMPLETE`, `INCOMPLETE`, `SLOW`).
  - `TimelineSegment(duration_seconds, blinks_per_minute=15.0, blink=ScriptedBlink.COMPLETE, face_present=True, head_yaw_degrees=0.0, iris_diameter_px=11.0)`, frozen.
  - `generate_samples(segments: Iterable[TimelineSegment], fps: float = 20.0, start: float = 0.0) -> Iterator[FaceSample]`. Each segment with a positive rate puts a blink at its start, then one every `60 / rate` seconds. COMPLETE = 150 ms at 20% of open EAR; INCOMPLETE = 150 ms at 55%; SLOW = 400 ms at 20%.
  - `ScriptedFaceSampleSource(segments: Sequence[TimelineSegment], fps: float, clock: Clock, sleep: Callable[[float], None] = time.sleep)`: loops the timeline forever, sleeping `1/fps` per sample and stamping samples with `clock.now()`.
  - `SCENARIOS: dict[str, tuple[TimelineSegment, ...]]` with keys `normal`, `low-blink-rate`, `incomplete-blinks`, `too-close`, `away`.
  - Fake `RecordingSleeper` with `.calls: list[float]`.

- [ ] **Step 1: Write the fake**

`tests/fakes/sleeper.py`:

```python
class RecordingSleeper:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
```

- [ ] **Step 2: Write the failing tests**

`tests/unit/test_scripted.py`:

```python
from collections.abc import Iterable

import pytest

from spare_my_eyes.analysis.blink_detector import Blink, BlinkDetector, BlinkKind
from spare_my_eyes.capture.camera_errors import CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import UnavailableSampleSource
from spare_my_eyes.capture.scenarios import SCENARIOS
from spare_my_eyes.capture.scripted import (
    OPEN_EAR,
    ScriptedBlink,
    ScriptedFaceSampleSource,
    TimelineSegment,
    generate_samples,
)
from tests.fakes.clock import FakeClock
from tests.fakes.sleeper import RecordingSleeper


def detected_blinks(samples: Iterable[FaceSample]) -> list[Blink]:
    detector = BlinkDetector(OPEN_EAR)
    return [blink for sample in samples if (blink := detector.update(sample)) is not None]


def scripted_source(duration: float, sleeper: RecordingSleeper) -> ScriptedFaceSampleSource:
    return ScriptedFaceSampleSource([TimelineSegment(duration)], 20.0, FakeClock(100.0), sleeper)


def test_generate_samples_one_second_segment_produces_frames_at_fps() -> None:
    samples = list(generate_samples([TimelineSegment(1.0)], fps=20.0))
    assert len(samples) == 20
    assert samples[-1].timestamp == pytest.approx(0.95)


def test_generate_samples_blink_rate_produces_matching_blink_count() -> None:
    blinks = detected_blinks(generate_samples([TimelineSegment(60.0, blinks_per_minute=12.0)]))
    assert len(blinks) == 12
    assert {blink.kind for blink in blinks} == {BlinkKind.COMPLETE}


def test_generate_samples_incomplete_blinks_are_classified_incomplete() -> None:
    segment = TimelineSegment(30.0, blinks_per_minute=12.0, blink=ScriptedBlink.INCOMPLETE)
    blinks = detected_blinks(generate_samples([segment]))
    assert {blink.kind for blink in blinks} == {BlinkKind.INCOMPLETE}


def test_generate_samples_slow_blinks_last_between_300_and_500_ms() -> None:
    segment = TimelineSegment(10.0, blinks_per_minute=30.0, blink=ScriptedBlink.SLOW)
    blinks = detected_blinks(generate_samples([segment]))
    assert len(blinks) == 5
    assert all(0.3 <= blink.duration_seconds <= 0.5 for blink in blinks)


def test_generate_samples_zero_blink_rate_keeps_eyes_open() -> None:
    samples = generate_samples([TimelineSegment(5.0, blinks_per_minute=0.0)])
    assert {sample.mean_ear for sample in samples} == {OPEN_EAR}


def test_generate_samples_absent_segment_has_no_face() -> None:
    samples = generate_samples([TimelineSegment(1.0, face_present=False)])
    assert not any(sample.face_present for sample in samples)


def test_generate_samples_consecutive_segments_continue_timestamps() -> None:
    samples = list(generate_samples([TimelineSegment(1.0), TimelineSegment(1.0)], start=10.0))
    assert samples[20].timestamp == pytest.approx(11.0)
    assert samples[-1].timestamp == pytest.approx(11.95)


def test_next_sample_scripted_source_paces_and_stamps_with_clock() -> None:
    sleeper = RecordingSleeper()
    source = scripted_source(1.0, sleeper)
    source.open()
    assert source.next_sample().timestamp == 100.0
    assert sleeper.calls == [pytest.approx(0.05)]


def test_next_sample_scripted_source_loops_after_timeline_ends() -> None:
    source = scripted_source(0.1, RecordingSleeper())
    source.open()
    samples = [source.next_sample() for _ in range(5)]
    assert all(sample.face_present for sample in samples)


def test_next_sample_before_open_raises_camera_unavailable() -> None:
    with pytest.raises(CameraUnavailableError):
        scripted_source(1.0, RecordingSleeper()).next_sample()


def test_open_unavailable_source_raises_with_reason() -> None:
    with pytest.raises(CameraUnavailableError, match="model missing"):
        UnavailableSampleSource("model missing at C:/x.task").open()


def test_scenarios_every_name_has_segments() -> None:
    assert set(SCENARIOS) == {"normal", "low-blink-rate", "incomplete-blinks", "too-close", "away"}
    assert all(SCENARIOS.values())
```

- [ ] **Step 3: Run to see them fail**

Run: `uv run pytest tests/unit/test_scripted.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.capture.camera_errors'`.

- [ ] **Step 4: Implement errors and the source interface**

`src/spare_my_eyes/capture/camera_errors.py`:

```python
class CameraUnavailableError(Exception):
    pass


class CameraBusyError(Exception):
    pass
```

`src/spare_my_eyes/capture/sample_source.py`:

```python
from enum import StrEnum
from typing import Protocol

from spare_my_eyes.capture.camera_errors import CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample


class CameraStatus(StrEnum):
    ACTIVE = "active"
    UNAVAILABLE = "unavailable"
    BUSY = "busy"


class FaceSampleSource(Protocol):
    def open(self) -> None: ...

    def next_sample(self) -> FaceSample: ...

    def close(self) -> None: ...


class UnavailableSampleSource:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def open(self) -> None:
        raise CameraUnavailableError(self._reason)

    def next_sample(self) -> FaceSample:
        raise CameraUnavailableError(self._reason)

    def close(self) -> None:
        return None
```

- [ ] **Step 5: Implement the scripted timeline**

`src/spare_my_eyes/capture/scripted.py`:

```python
import itertools
import math
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from spare_my_eyes.capture.camera_errors import CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.clock import Clock

OPEN_EAR = 0.30
DEFAULT_IRIS_DIAMETER_PX = 11.0
_TOLERANCE = 1e-9


class ScriptedBlink(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    SLOW = "slow"


@dataclass(frozen=True, slots=True)
class _BlinkShape:
    duration_seconds: float
    ear_ratio: float


_SHAPES = {
    ScriptedBlink.COMPLETE: _BlinkShape(0.15, 0.2),
    ScriptedBlink.INCOMPLETE: _BlinkShape(0.15, 0.55),
    ScriptedBlink.SLOW: _BlinkShape(0.4, 0.2),
}


@dataclass(frozen=True, slots=True)
class TimelineSegment:
    duration_seconds: float
    blinks_per_minute: float = 15.0
    blink: ScriptedBlink = ScriptedBlink.COMPLETE
    face_present: bool = True
    head_yaw_degrees: float = 0.0
    iris_diameter_px: float = DEFAULT_IRIS_DIAMETER_PX


def generate_samples(
    segments: Iterable[TimelineSegment], fps: float = 20.0, start: float = 0.0
) -> Iterator[FaceSample]:
    segment_start = start
    for segment in segments:
        yield from _segment_samples(segment, fps, segment_start)
        segment_start += segment.duration_seconds


def _segment_samples(segment: TimelineSegment, fps: float, start: float) -> Iterator[FaceSample]:
    for index in range(round(segment.duration_seconds * fps)):
        offset = index / fps
        yield _sample_at(segment, start + offset, _blink_phase(offset, segment.blinks_per_minute))


def _blink_phase(offset: float, blinks_per_minute: float) -> float:
    if blinks_per_minute <= 0:
        return math.inf
    return offset % (60.0 / blinks_per_minute)


def _sample_at(segment: TimelineSegment, timestamp: float, phase: float) -> FaceSample:
    if not segment.face_present:
        return FaceSample.absent(timestamp)
    shape = _SHAPES[segment.blink]
    ratio = shape.ear_ratio if phase < shape.duration_seconds - _TOLERANCE else 1.0
    ear = OPEN_EAR * ratio
    return FaceSample(
        timestamp=timestamp,
        face_present=True,
        left_ear=ear,
        right_ear=ear,
        iris_diameter_px=segment.iris_diameter_px,
        head_yaw_degrees=segment.head_yaw_degrees,
    )


class ScriptedFaceSampleSource:
    """Replays a scripted timeline in real time, for demos and the app smoke test."""

    def __init__(
        self,
        segments: Sequence[TimelineSegment],
        fps: float,
        clock: Clock,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not segments:
            raise ValueError(f"Scripted timeline needs at least one segment, got {segments!r}")
        self._segments = tuple(segments)
        self._fps = fps
        self._clock = clock
        self._sleep = sleep
        self._samples: Iterator[FaceSample] | None = None

    def open(self) -> None:
        self._samples = generate_samples(itertools.cycle(self._segments), self._fps)

    def next_sample(self) -> FaceSample:
        if self._samples is None:
            raise CameraUnavailableError("Scripted source was read before open()")
        self._sleep(1.0 / self._fps)
        return replace(next(self._samples), timestamp=self._clock.now())

    def close(self) -> None:
        self._samples = None
```

`src/spare_my_eyes/capture/scenarios.py`:

```python
from spare_my_eyes.capture.scripted import ScriptedBlink, TimelineSegment

SCENARIOS: dict[str, tuple[TimelineSegment, ...]] = {
    "normal": (TimelineSegment(60.0),),
    "low-blink-rate": (TimelineSegment(180.0, blinks_per_minute=4.8),),
    "incomplete-blinks": (
        TimelineSegment(180.0, blinks_per_minute=4.8, blink=ScriptedBlink.INCOMPLETE),
    ),
    "too-close": (TimelineSegment(60.0, iris_diameter_px=15.0),),
    "away": (TimelineSegment(30.0), TimelineSegment(90.0, face_present=False)),
}
```

- [ ] **Step 6: Run to see them pass**

Run: `uv run pytest tests/unit/test_scripted.py -v && uv run mypy`
Expected: 12 passed, mypy clean.

- [ ] **Step 7: Commit**

```bash
git add src/spare_my_eyes/capture tests/fakes/sleeper.py tests/unit/test_scripted.py
git commit -m "feat: add scripted face-sample timeline and sample source interface

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: Notifier interface and BlinkNudgePolicy

**Files:**
- Create: `src/spare_my_eyes/coaching/notifier.py`, `src/spare_my_eyes/coaching/blink_nudge.py`
- Create: `tests/fakes/notifier.py`, `tests/fakes/timeline.py`
- Test: `tests/unit/test_blink_nudge.py`

**Interfaces:**
- Consumes: `BlinkDetector`, `BlinkKind`, `BlinkRateMonitor`, `BlinkStats` (Tasks 4–5), `Cooldown` (Task 10), `BreakProgress` (Task 11), `CalibrationProgress` (Task 9), `generate_samples`, `TimelineSegment`, `OPEN_EAR` (Task 12), `FakeClock`.
- Produces:
  - `TrayStatus` (StrEnum): `MONITORING`, `PAUSED`, `NO_CAMERA`, `CALIBRATING`.
  - `Notifier` protocol: `show_blink_nudge(message: str)`, `hide_blink_nudge()`, `show_distance_alert(message: str)`, `hide_distance_alert()`, `show_break(progress: BreakProgress)` (creates or updates the card), `hide_break()`, `show_calibration(progress: CalibrationProgress)`, `hide_calibration()`, `set_status(status: TrayStatus, blinks_per_minute: float | None)`. All return `None`.
  - `BLINK_MESSAGE = "Blink"`, `SLOW_BLINK_MESSAGE = "Blink slowly, close fully"`.
  - `BlinkNudgeRules(rate_threshold_per_minute=8.0, incomplete_ratio_threshold=0.3, max_visible_seconds=8.0, hide_after_complete_blinks=2, cooldown_seconds=180.0)`, frozen.
  - `BlinkNudgePolicy(detector: BlinkDetector, monitor: BlinkRateMonitor, rules: BlinkNudgeRules, notifier: Notifier)` with `on_sample(sample)`, `on_tick(now)`, `suspend()`, `current_rate() -> float | None`.
  - Fakes: `RecordingNotifier` (state attributes `blink_nudge`, `distance_alert`, `break_progress`, `calibration`, `status`, `blinks_per_minute`; `calls: list[NotifierCall]`; `count(name) -> int`); `TimelineDriver(clock: FakeClock, on_sample: Callable[[FaceSample], None], on_tick: Callable[[], None])` with `play(*segments)` and `pass_time(seconds: int)`, ticking once per simulated second.

- [ ] **Step 1: Write the Notifier interface (needed by the fakes)**

`src/spare_my_eyes/coaching/notifier.py`:

```python
from enum import StrEnum
from typing import Protocol

from spare_my_eyes.calibration import CalibrationProgress
from spare_my_eyes.coaching.break_session import BreakProgress


class TrayStatus(StrEnum):
    MONITORING = "monitoring"
    PAUSED = "paused"
    NO_CAMERA = "no_camera"
    CALIBRATING = "calibrating"


class Notifier(Protocol):
    def show_blink_nudge(self, message: str) -> None: ...

    def hide_blink_nudge(self) -> None: ...

    def show_distance_alert(self, message: str) -> None: ...

    def hide_distance_alert(self) -> None: ...

    def show_break(self, progress: BreakProgress) -> None: ...

    def hide_break(self) -> None: ...

    def show_calibration(self, progress: CalibrationProgress) -> None: ...

    def hide_calibration(self) -> None: ...

    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None: ...
```

- [ ] **Step 2: Write the fakes**

`tests/fakes/notifier.py`:

```python
from dataclasses import dataclass

from spare_my_eyes.calibration import CalibrationProgress
from spare_my_eyes.coaching.break_session import BreakProgress
from spare_my_eyes.coaching.notifier import TrayStatus


@dataclass(frozen=True, slots=True)
class NotifierCall:
    name: str
    argument: object = None


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[NotifierCall] = []
        self.blink_nudge: str | None = None
        self.distance_alert: str | None = None
        self.break_progress: BreakProgress | None = None
        self.calibration: CalibrationProgress | None = None
        self.status: TrayStatus | None = None
        self.blinks_per_minute: float | None = None

    def count(self, name: str) -> int:
        return sum(1 for call in self.calls if call.name == name)

    def show_blink_nudge(self, message: str) -> None:
        self.calls.append(NotifierCall("show_blink_nudge", message))
        self.blink_nudge = message

    def hide_blink_nudge(self) -> None:
        self.calls.append(NotifierCall("hide_blink_nudge"))
        self.blink_nudge = None

    def show_distance_alert(self, message: str) -> None:
        self.calls.append(NotifierCall("show_distance_alert", message))
        self.distance_alert = message

    def hide_distance_alert(self) -> None:
        self.calls.append(NotifierCall("hide_distance_alert"))
        self.distance_alert = None

    def show_break(self, progress: BreakProgress) -> None:
        self.calls.append(NotifierCall("show_break", progress))
        self.break_progress = progress

    def hide_break(self) -> None:
        self.calls.append(NotifierCall("hide_break"))
        self.break_progress = None

    def show_calibration(self, progress: CalibrationProgress) -> None:
        self.calls.append(NotifierCall("show_calibration", progress))
        self.calibration = progress

    def hide_calibration(self) -> None:
        self.calls.append(NotifierCall("hide_calibration"))
        self.calibration = None

    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None:
        self.calls.append(NotifierCall("set_status", status))
        self.status = status
        self.blinks_per_minute = blinks_per_minute
```

`tests/fakes/timeline.py`:

```python
from collections.abc import Callable

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.scripted import TimelineSegment, generate_samples
from tests.fakes.clock import FakeClock


class TimelineDriver:
    """Plays scripted face samples on a fake clock and ticks once per simulated second."""

    FPS = 20.0
    TICK_SECONDS = 1.0

    def __init__(
        self,
        clock: FakeClock,
        on_sample: Callable[[FaceSample], None],
        on_tick: Callable[[], None],
    ) -> None:
        self._clock = clock
        self._on_sample = on_sample
        self._on_tick = on_tick
        self._next_tick_at = clock.now()

    def play(self, *segments: TimelineSegment) -> None:
        start = self._clock.now()
        for sample in generate_samples(segments, self.FPS, start):
            self._clock.set(sample.timestamp)
            self._on_sample(sample)
            self._tick_when_due()
        self._clock.set(start + sum(segment.duration_seconds for segment in segments))

    def pass_time(self, seconds: int) -> None:
        for _ in range(seconds):
            self._clock.advance(self.TICK_SECONDS)
            self._tick_when_due()

    def _tick_when_due(self) -> None:
        if self._clock.now() + 1e-9 < self._next_tick_at:
            return
        self._on_tick()
        self._next_tick_at = self._clock.now() + self.TICK_SECONDS
```

- [ ] **Step 3: Write the failing tests**

`tests/unit/test_blink_nudge.py`:

```python
from dataclasses import dataclass

import pytest

from spare_my_eyes.analysis.blink_detector import BlinkDetector
from spare_my_eyes.analysis.blink_rate import BlinkRateMonitor
from spare_my_eyes.capture.scripted import OPEN_EAR, ScriptedBlink, TimelineSegment
from spare_my_eyes.coaching.blink_nudge import (
    BLINK_MESSAGE,
    SLOW_BLINK_MESSAGE,
    BlinkNudgePolicy,
    BlinkNudgeRules,
)
from tests.fakes.clock import FakeClock
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.timeline import TimelineDriver

LOW_RATE = 4.8


@dataclass
class NudgeRig:
    policy: BlinkNudgePolicy
    notifier: RecordingNotifier
    driver: TimelineDriver


@pytest.fixture
def rig() -> NudgeRig:
    clock = FakeClock()
    notifier = RecordingNotifier()
    policy = BlinkNudgePolicy(
        BlinkDetector(OPEN_EAR), BlinkRateMonitor(120.0), BlinkNudgeRules(), notifier
    )
    driver = TimelineDriver(clock, policy.on_sample, lambda: policy.on_tick(clock.now()))
    return NudgeRig(policy, notifier, driver)


def test_on_sample_low_rate_for_full_window_shows_blink_nudge(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.blink_nudge == BLINK_MESSAGE


def test_on_sample_normal_rate_shows_nothing(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(130.0, blinks_per_minute=15.0))
    assert rig.notifier.count("show_blink_nudge") == 0


def test_on_sample_low_rate_before_window_is_full_shows_nothing(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(60.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.blink_nudge is None


def test_on_sample_two_complete_blinks_hide_nudge(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.driver.play(TimelineSegment(0.5, blinks_per_minute=60.0))
    assert rig.notifier.blink_nudge == BLINK_MESSAGE
    rig.driver.play(TimelineSegment(0.5, blinks_per_minute=60.0))
    assert rig.notifier.blink_nudge is None


def test_on_sample_incomplete_blinks_do_not_hide_nudge(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.driver.play(
        TimelineSegment(3.0, blinks_per_minute=60.0, blink=ScriptedBlink.INCOMPLETE)
    )
    assert rig.notifier.blink_nudge == BLINK_MESSAGE


def test_on_tick_nudge_visible_for_eight_seconds_hides_it(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.driver.play(TimelineSegment(9.0, blinks_per_minute=0.0))
    assert rig.notifier.blink_nudge is None


def test_on_sample_within_cooldown_does_not_show_again(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.driver.play(TimelineSegment(9.0, blinks_per_minute=0.0))
    rig.driver.play(TimelineSegment(170.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.count("show_blink_nudge") == 1
    rig.driver.play(TimelineSegment(15.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.count("show_blink_nudge") == 2


def test_on_sample_mostly_incomplete_blinks_uses_slow_blink_wording(rig: NudgeRig) -> None:
    rig.driver.play(
        TimelineSegment(121.0, blinks_per_minute=LOW_RATE, blink=ScriptedBlink.INCOMPLETE)
    )
    assert rig.notifier.blink_nudge == SLOW_BLINK_MESSAGE


def test_suspend_visible_nudge_hides_it_and_clears_window(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    rig.policy.suspend()
    assert rig.notifier.blink_nudge is None
    rig.driver.play(TimelineSegment(60.0, blinks_per_minute=LOW_RATE))
    assert rig.notifier.blink_nudge is None


def test_current_rate_before_samples_returns_none(rig: NudgeRig) -> None:
    assert rig.policy.current_rate() is None


def test_current_rate_after_normal_blinking_reports_rate(rig: NudgeRig) -> None:
    rig.driver.play(TimelineSegment(60.0, blinks_per_minute=15.0))
    assert rig.policy.current_rate() == pytest.approx(15.0, abs=0.5)
```

- [ ] **Step 4: Run to see them fail**

Run: `uv run pytest tests/unit/test_blink_nudge.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.coaching.blink_nudge'`.

- [ ] **Step 5: Implement**

`src/spare_my_eyes/coaching/blink_nudge.py`:

```python
from dataclasses import dataclass

from spare_my_eyes.analysis.blink_detector import Blink, BlinkDetector, BlinkKind
from spare_my_eyes.analysis.blink_rate import BlinkRateMonitor, BlinkStats
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.coaching.cooldown import Cooldown
from spare_my_eyes.coaching.notifier import Notifier

BLINK_MESSAGE = "Blink"
SLOW_BLINK_MESSAGE = "Blink slowly, close fully"


@dataclass(frozen=True, slots=True)
class BlinkNudgeRules:
    rate_threshold_per_minute: float = 8.0
    incomplete_ratio_threshold: float = 0.3
    max_visible_seconds: float = 8.0
    hide_after_complete_blinks: int = 2
    cooldown_seconds: float = 180.0


class BlinkNudgePolicy:
    def __init__(
        self,
        detector: BlinkDetector,
        monitor: BlinkRateMonitor,
        rules: BlinkNudgeRules,
        notifier: Notifier,
    ) -> None:
        self._detector = detector
        self._monitor = monitor
        self._rules = rules
        self._notifier = notifier
        self._cooldown = Cooldown(rules.cooldown_seconds)
        self._shown_at: float | None = None
        self._complete_blinks_while_shown = 0

    def on_sample(self, sample: FaceSample) -> None:
        blink = self._detector.update(sample)
        self._monitor.observe(sample)
        if blink is not None:
            self._monitor.record(blink)
            self._count_toward_hiding(blink)
        self._show_when_needed(sample.timestamp)

    def on_tick(self, now: float) -> None:
        if self._shown_at is None:
            return
        if now - self._shown_at >= self._rules.max_visible_seconds:
            self._hide(now)

    def suspend(self) -> None:
        if self._shown_at is not None:
            self._notifier.hide_blink_nudge()
        self._shown_at = None
        self._detector.reset()
        self._monitor.reset()
        self._cooldown.clear()

    def current_rate(self) -> float | None:
        stats = self._monitor.stats()
        return None if stats is None else stats.blinks_per_minute

    def _count_toward_hiding(self, blink: Blink) -> None:
        if self._shown_at is None or blink.kind is not BlinkKind.COMPLETE:
            return
        self._complete_blinks_while_shown += 1
        if self._complete_blinks_while_shown >= self._rules.hide_after_complete_blinks:
            self._hide(blink.ended_at)

    def _show_when_needed(self, now: float) -> None:
        if self._shown_at is not None or not self._cooldown.is_ready(now):
            return
        stats = self._monitor.stats()
        if stats is None or not self._is_rate_low(stats):
            return
        self._notifier.show_blink_nudge(self._message_for(stats))
        self._shown_at = now
        self._complete_blinks_while_shown = 0

    def _is_rate_low(self, stats: BlinkStats) -> bool:
        return stats.window_full and stats.blinks_per_minute < self._rules.rate_threshold_per_minute

    def _message_for(self, stats: BlinkStats) -> str:
        if stats.incomplete_ratio > self._rules.incomplete_ratio_threshold:
            return SLOW_BLINK_MESSAGE
        return BLINK_MESSAGE

    def _hide(self, now: float) -> None:
        self._notifier.hide_blink_nudge()
        self._shown_at = None
        self._cooldown.start(now)
```

- [ ] **Step 6: Run to see them pass**

Run: `uv run pytest tests/unit/test_blink_nudge.py -v && uv run mypy`
Expected: 11 passed, mypy clean.

- [ ] **Step 7: Commit**

```bash
git add src/spare_my_eyes/coaching/notifier.py src/spare_my_eyes/coaching/blink_nudge.py tests/fakes/notifier.py tests/fakes/timeline.py tests/unit/test_blink_nudge.py
git commit -m "feat: nudge the user when blink rate stays low

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: DistanceAlertPolicy

**Files:**
- Create: `src/spare_my_eyes/coaching/distance_alert.py`
- Test: `tests/unit/test_distance_alert.py`

**Interfaces:**
- Consumes: `ScreenDistanceEstimator` (Task 6), `Cooldown`, `Notifier`, `TimelineDriver`, `RecordingNotifier`.
- Produces:
  - `MOVE_BACK_MESSAGE = "Move back a little"`.
  - `DistanceAlertPolicy(estimator: ScreenDistanceEstimator, cooldown: Cooldown, notifier: Notifier)` with `on_sample(sample)`, `on_tick(now)`, `suspend()`.

Hold time and hysteresis live in the estimator. The policy adds only the 5-minute cooldown after the alert hides.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_distance_alert.py`:

```python
from dataclasses import dataclass

import pytest

from spare_my_eyes.analysis.distance import ScreenDistanceEstimator
from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.cooldown import Cooldown
from spare_my_eyes.coaching.distance_alert import MOVE_BACK_MESSAGE, DistanceAlertPolicy
from tests.fakes.clock import FakeClock
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.timeline import TimelineDriver

FOCAL_SCALE = 660.0


def at_cm(duration: float, centimeters: float) -> TimelineSegment:
    return TimelineSegment(duration, iris_diameter_px=FOCAL_SCALE / centimeters)


@dataclass
class DistanceRig:
    policy: DistanceAlertPolicy
    notifier: RecordingNotifier
    driver: TimelineDriver


@pytest.fixture
def rig() -> DistanceRig:
    clock = FakeClock()
    notifier = RecordingNotifier()
    policy = DistanceAlertPolicy(
        ScreenDistanceEstimator(FOCAL_SCALE), Cooldown(300.0), notifier
    )
    driver = TimelineDriver(clock, policy.on_sample, lambda: policy.on_tick(clock.now()))
    return DistanceRig(policy, notifier, driver)


def test_on_sample_far_from_screen_shows_nothing(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(60.0, 60.0))
    assert rig.notifier.distance_alert is None


def test_on_sample_close_for_less_than_thirty_seconds_shows_nothing(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(29.0, 45.0))
    assert rig.notifier.distance_alert is None


def test_on_sample_close_for_thirty_seconds_shows_alert(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(31.0, 45.0))
    assert rig.notifier.distance_alert == MOVE_BACK_MESSAGE


def test_on_sample_between_thresholds_keeps_alert_until_clear(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(31.0, 45.0))
    rig.driver.play(at_cm(10.0, 52.0))
    assert rig.notifier.distance_alert == MOVE_BACK_MESSAGE
    rig.driver.play(at_cm(5.0, 58.0))
    assert rig.notifier.distance_alert is None


def test_on_sample_close_again_within_cooldown_waits_for_cooldown(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(31.0, 45.0))
    rig.driver.play(at_cm(5.0, 58.0))
    rig.driver.play(at_cm(60.0, 45.0))
    assert rig.notifier.distance_alert is None
    rig.driver.play(at_cm(250.0, 45.0))
    assert rig.notifier.count("show_distance_alert") == 2


def test_suspend_visible_alert_hides_it_and_restarts_hold(rig: DistanceRig) -> None:
    rig.driver.play(at_cm(31.0, 45.0))
    rig.policy.suspend()
    assert rig.notifier.distance_alert is None
    rig.driver.play(at_cm(10.0, 45.0))
    assert rig.notifier.distance_alert is None
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_distance_alert.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.coaching.distance_alert'`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/coaching/distance_alert.py`:

```python
from spare_my_eyes.analysis.distance import DistanceReading, ScreenDistanceEstimator
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.coaching.cooldown import Cooldown
from spare_my_eyes.coaching.notifier import Notifier

MOVE_BACK_MESSAGE = "Move back a little"


class DistanceAlertPolicy:
    def __init__(
        self, estimator: ScreenDistanceEstimator, cooldown: Cooldown, notifier: Notifier
    ) -> None:
        self._estimator = estimator
        self._cooldown = cooldown
        self._notifier = notifier
        self._visible = False

    def on_sample(self, sample: FaceSample) -> None:
        reading = self._estimator.update(sample)
        if reading is None:
            return
        if self._visible:
            self._hide_when_clear(reading, sample.timestamp)
            return
        if reading.too_close and self._cooldown.is_ready(sample.timestamp):
            self._notifier.show_distance_alert(MOVE_BACK_MESSAGE)
            self._visible = True

    def on_tick(self, now: float) -> None:
        return None

    def suspend(self) -> None:
        if self._visible:
            self._notifier.hide_distance_alert()
        self._visible = False
        self._estimator.reset()

    def _hide_when_clear(self, reading: DistanceReading, now: float) -> None:
        if reading.too_close:
            return
        self._notifier.hide_distance_alert()
        self._visible = False
        self._cooldown.start(now)
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit/test_distance_alert.py -v && uv run mypy`
Expected: 6 passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/coaching/distance_alert.py tests/unit/test_distance_alert.py
git commit -m "feat: alert when sitting too close to the screen

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 15: Idle time and BreakPolicy

**Files:**
- Create: `src/spare_my_eyes/system/__init__.py`, `src/spare_my_eyes/system/idle_time.py`
- Create: `src/spare_my_eyes/coaching/break_policy.py`
- Create: `tests/fakes/idle_time.py`
- Test: `tests/unit/test_break_policy.py`, `tests/integration/test_windows_idle_time.py`

**Interfaces:**
- Consumes: `BreakSession`, `BreakTargets` (Task 11), `ScreenTimeCounter` (Task 10), `WindowGazeDetector`, `PresenceTracker`, `PresenceUpdate` (Task 7), `Notifier`, `Clock`, `TimelineDriver`.
- Produces:
  - `IdleTimeProvider` protocol: `idle_seconds() -> float` (seconds since last keyboard/mouse input). `WindowsIdleTimeProvider` (GetLastInputInfo).
  - `BreakSchedule(interval_seconds=1200.0, snooze_seconds=300.0, absence_reset_seconds=300.0)`, frozen.
  - `BreakPolicy(schedule: BreakSchedule, targets: BreakTargets, gaze: WindowGazeDetector, presence: PresenceTracker, open_ear_baseline: float, notifier: Notifier, clock: Clock)` with `on_sample(sample)`, `on_tick(now: float, idle_seconds: float)`, `start_now()`, `snooze()`, `skip()`, `suspend()`, `use_camera()`, `use_idle_time()`, property `screen_time_seconds -> float`.
  - Fake `FakeIdleTimeProvider(seconds: float = 0.0)` with a writable `.seconds`.

Presence for the screen-time counter is the latest of "face seen" (when the camera is active) and "last input". A break is camera-verified only if the camera saw a face in the last 5 s when the break starts. Otherwise it runs on the honor system and progresses while the user stays idle for ≥ 3 s.

- [ ] **Step 1: Write the fake**

`tests/fakes/idle_time.py`:

```python
class FakeIdleTimeProvider:
    def __init__(self, seconds: float = 0.0) -> None:
        self.seconds = seconds

    def idle_seconds(self) -> float:
        return self.seconds
```

- [ ] **Step 2: Write the failing tests**

`tests/integration/test_windows_idle_time.py`:

```python
from spare_my_eyes.system.idle_time import WindowsIdleTimeProvider


def test_idle_seconds_real_windows_session_returns_non_negative_seconds() -> None:
    assert 0.0 <= WindowsIdleTimeProvider().idle_seconds() < 50 * 24 * 3600
```

`tests/unit/test_break_policy.py`:

```python
from dataclasses import dataclass

import pytest

from spare_my_eyes.analysis.gaze import WindowGazeDetector, WindowSide
from spare_my_eyes.analysis.presence import PresenceTracker
from spare_my_eyes.capture.scripted import OPEN_EAR, ScriptedBlink, TimelineSegment
from spare_my_eyes.coaching.break_policy import BreakPolicy, BreakSchedule
from spare_my_eyes.coaching.break_session import BreakStep, BreakTargets
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.timeline import TimelineDriver

INTERVAL = 300.0
USER_NOT_TYPING = 10_000.0


@dataclass
class BreakRig:
    policy: BreakPolicy
    notifier: RecordingNotifier
    idle: FakeIdleTimeProvider
    driver: TimelineDriver


@pytest.fixture
def rig() -> BreakRig:
    clock = FakeClock()
    notifier = RecordingNotifier()
    idle = FakeIdleTimeProvider(USER_NOT_TYPING)
    schedule = BreakSchedule(interval_seconds=INTERVAL, snooze_seconds=30.0)
    policy = BreakPolicy(
        schedule,
        BreakTargets(),
        WindowGazeDetector(WindowSide.LEFT),
        PresenceTracker(60.0),
        OPEN_EAR,
        notifier,
        clock,
    )
    driver = TimelineDriver(
        clock, policy.on_sample, lambda: policy.on_tick(clock.now(), idle.idle_seconds())
    )
    return BreakRig(policy, notifier, idle, driver)


def test_on_tick_before_interval_shows_nothing(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL - 2.0))
    assert rig.notifier.break_progress is None


def test_on_tick_screen_time_reaches_interval_shows_verified_break(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    progress = rig.notifier.break_progress
    assert progress is not None
    assert progress.step is BreakStep.LOOK_OUT
    assert progress.verified


def test_on_sample_gaze_then_slow_blinks_complete_break_and_reset_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    rig.driver.play(TimelineSegment(21.0, head_yaw_degrees=-30.0))
    rig.driver.play(TimelineSegment(10.5, blinks_per_minute=30.0, blink=ScriptedBlink.SLOW))
    assert rig.notifier.break_progress is None
    assert rig.policy.screen_time_seconds < 15.0


def test_snooze_open_break_hides_it_until_snooze_ends(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    rig.policy.snooze()
    assert rig.notifier.break_progress is None
    rig.driver.play(TimelineSegment(28.0))
    assert rig.notifier.break_progress is None
    rig.driver.play(TimelineSegment(4.0))
    assert rig.notifier.break_progress is not None


def test_skip_open_break_hides_it_and_resets_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    rig.policy.skip()
    assert rig.notifier.break_progress is None
    assert rig.policy.screen_time_seconds == 0.0


def test_on_tick_no_face_but_user_typing_starts_unverified_break(rig: BreakRig) -> None:
    rig.idle.seconds = 0.0
    rig.driver.play(TimelineSegment(INTERVAL + 2.0, face_present=False))
    progress = rig.notifier.break_progress
    assert progress is not None
    assert not progress.verified


def test_on_tick_absence_shorter_than_five_minutes_pauses_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(100.0))
    rig.driver.play(TimelineSegment(200.0, face_present=False))
    rig.driver.play(TimelineSegment(10.0))
    assert rig.policy.screen_time_seconds == pytest.approx(170.0, abs=3.0)


def test_on_tick_absence_of_five_minutes_resets_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(100.0))
    rig.driver.play(TimelineSegment(301.0, face_present=False))
    rig.driver.play(TimelineSegment(10.0))
    assert rig.policy.screen_time_seconds < 15.0


def test_suspend_open_break_hides_it_and_resets_counter(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(INTERVAL + 2.0))
    rig.policy.suspend()
    assert rig.notifier.break_progress is None
    assert rig.policy.screen_time_seconds == 0.0


def test_use_idle_time_camera_off_runs_unverified_break_from_input(rig: BreakRig) -> None:
    rig.policy.use_idle_time()
    rig.idle.seconds = 0.0
    rig.driver.pass_time(int(INTERVAL) + 2)
    progress = rig.notifier.break_progress
    assert progress is not None
    assert not progress.verified


def test_start_now_shows_break_immediately(rig: BreakRig) -> None:
    rig.driver.play(TimelineSegment(5.0))
    rig.policy.start_now()
    assert rig.notifier.break_progress is not None
```

- [ ] **Step 3: Run to see them fail**

Run: `uv run pytest tests/unit/test_break_policy.py tests/integration/test_windows_idle_time.py -v`
Expected: FAIL with `ModuleNotFoundError` for `spare_my_eyes.coaching.break_policy` and `spare_my_eyes.system`.

- [ ] **Step 4: Implement idle time**

`src/spare_my_eyes/system/__init__.py`: empty.

`src/spare_my_eyes/system/idle_time.py`:

```python
import ctypes
from typing import Protocol

_DWORD_MASK = 0xFFFFFFFF


class IdleTimeProvider(Protocol):
    def idle_seconds(self) -> float: ...


class _LastInputInfo(ctypes.Structure):
    _fields_ = (("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint))


class WindowsIdleTimeProvider:
    def idle_seconds(self) -> float:
        info = _LastInputInfo()
        info.cbSize = ctypes.sizeof(_LastInputInfo)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            raise OSError(
                f"GetLastInputInfo failed with error {ctypes.GetLastError()}; "
                "expected a nonzero return"
            )
        now_ms = int(ctypes.windll.kernel32.GetTickCount()) & _DWORD_MASK
        last_input_ms = int(info.dwTime) & _DWORD_MASK
        return float((now_ms - last_input_ms) & _DWORD_MASK) / 1000.0
```

- [ ] **Step 5: Implement BreakPolicy**

`src/spare_my_eyes/coaching/break_policy.py`:

```python
import math
from dataclasses import dataclass

from spare_my_eyes.analysis.gaze import WindowGazeDetector
from spare_my_eyes.analysis.presence import PresenceTracker, PresenceUpdate
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.break_session import BreakSession, BreakTargets
from spare_my_eyes.coaching.notifier import Notifier
from spare_my_eyes.coaching.screen_time import ScreenTimeCounter

IDLE_LOOKING_AWAY_SECONDS = 3.0
RECENT_FACE_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class BreakSchedule:
    interval_seconds: float = 1200.0
    snooze_seconds: float = 300.0
    absence_reset_seconds: float = 300.0


class BreakPolicy:
    """Counts screen time from face or keyboard presence and runs one break at a time."""

    def __init__(
        self,
        schedule: BreakSchedule,
        targets: BreakTargets,
        gaze: WindowGazeDetector,
        presence: PresenceTracker,
        open_ear_baseline: float,
        notifier: Notifier,
        clock: Clock,
    ) -> None:
        self._schedule = schedule
        self._targets = targets
        self._gaze = gaze
        self._presence = presence
        self._open_ear_baseline = open_ear_baseline
        self._notifier = notifier
        self._clock = clock
        self._screen_time = ScreenTimeCounter()
        self._session: BreakSession | None = None
        self._snoozed_until = -math.inf
        self._camera_active = True
        self._last_face_seen_at: float | None = None

    @property
    def screen_time_seconds(self) -> float:
        return self._screen_time.seconds

    def on_sample(self, sample: FaceSample) -> None:
        if sample.face_present:
            self._last_face_seen_at = sample.timestamp
        session = self._session
        if session is None or not session.is_verified:
            return
        looking = self._gaze.is_looking_at_window(sample)
        session.observe(sample.timestamp, looking, self._ear_ratio(sample))
        self._publish()

    def on_tick(self, now: float, idle_seconds: float) -> None:
        self._track_presence(now, idle_seconds)
        if self._session is None:
            self._start_when_due(now)
            return
        self._advance(self._session, now, idle_seconds)

    def start_now(self) -> None:
        if self._session is None:
            self._start(self._clock.now())

    def snooze(self) -> None:
        if self._session is None:
            return
        self._dismiss_card()
        self._snoozed_until = self._clock.now() + self._schedule.snooze_seconds

    def skip(self) -> None:
        if self._session is None:
            return
        self._session.skip()
        self._publish()

    def suspend(self) -> None:
        self._dismiss_card()
        self._screen_time.reset()
        self._snoozed_until = -math.inf

    def use_camera(self) -> None:
        self._camera_active = True

    def use_idle_time(self) -> None:
        self._camera_active = False

    def _advance(self, session: BreakSession, now: float, idle_seconds: float) -> None:
        if not session.is_verified:
            session.advance_unverified(now, idle_seconds >= IDLE_LOOKING_AWAY_SECONDS)
        session.check_timeout(now)
        self._publish()

    def _track_presence(self, now: float, idle_seconds: float) -> None:
        update = self._presence.update(now, self._latest_sighting(now, idle_seconds))
        if self._is_long_absence(update):
            self._screen_time.reset()
        if update.present:
            self._screen_time.add_presence(now)
        else:
            self._screen_time.pause()

    def _is_long_absence(self, update: PresenceUpdate) -> bool:
        absence = update.returned_after_seconds
        return absence is not None and absence >= self._schedule.absence_reset_seconds

    def _latest_sighting(self, now: float, idle_seconds: float) -> float:
        last_input_at = now - idle_seconds
        if not self._camera_active or self._last_face_seen_at is None:
            return last_input_at
        return max(self._last_face_seen_at, last_input_at)

    def _start_when_due(self, now: float) -> None:
        if self._screen_time.seconds < self._schedule.interval_seconds:
            return
        if now < self._snoozed_until:
            return
        self._start(now)

    def _start(self, now: float) -> None:
        if self._camera_sees_user(now):
            self._session = BreakSession.verified_by_camera(now, self._targets)
        else:
            self._session = BreakSession.on_honor_system(now, self._targets)
        self._publish()

    def _camera_sees_user(self, now: float) -> bool:
        seen_at = self._last_face_seen_at
        return self._camera_active and seen_at is not None and now - seen_at < RECENT_FACE_SECONDS

    def _ear_ratio(self, sample: FaceSample) -> float | None:
        return sample.mean_ear / self._open_ear_baseline if sample.face_present else None

    def _publish(self) -> None:
        if self._session is None:
            return
        if self._session.outcome is None:
            self._notifier.show_break(self._session.progress())
            return
        self._finish()

    def _finish(self) -> None:
        self._dismiss_card()
        self._screen_time.reset()
        self._snoozed_until = -math.inf

    def _dismiss_card(self) -> None:
        if self._session is None:
            return
        self._session = None
        self._notifier.hide_break()
```

- [ ] **Step 6: Run to see them pass**

Run: `uv run pytest tests/unit/test_break_policy.py tests/integration/test_windows_idle_time.py -v && uv run mypy`
Expected: 12 passed, mypy clean.

- [ ] **Step 7: Commit**

```bash
git add src/spare_my_eyes/system src/spare_my_eyes/coaching/break_policy.py tests/fakes/idle_time.py tests/unit/test_break_policy.py tests/integration/test_windows_idle_time.py
git commit -m "feat: schedule verified breaks from screen time with idle-time fallback

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 16: Coach, build_coach and the pipeline integration scenarios

**Files:**
- Create: `src/spare_my_eyes/coaching/coach.py`, `src/spare_my_eyes/coaching/factory.py`
- Create: `tests/fakes/policies.py`, `tests/integration/pipeline_run.py`
- Test: `tests/unit/test_coach.py`, `tests/integration/test_blink_nudge_pipeline.py`, `tests/integration/test_distance_pipeline.py`, `tests/integration/test_break_pipeline.py`, `tests/integration/test_camera_fallback_pipeline.py`

**Interfaces:**
- Consumes: everything from Tasks 4–15.
- Produces:
  - `CoachingPolicy` protocol: `on_sample(sample)`, `on_tick(now)`, `suspend()`.
  - `BreakControl` protocol: `on_sample(sample)`, `on_tick(now, idle_seconds)`, `start_now()`, `snooze()`, `skip()`, `suspend()`, `use_camera()`, `use_idle_time()` (satisfied by `BreakPolicy`).
  - `Coach(camera_policies: Sequence[CoachingPolicy], breaks: BreakControl, blink_rate: Callable[[], float | None], idle: IdleTimeProvider, notifier: Notifier, clock: Clock)` with `on_sample(sample)`, `tick()`, `pause_for(seconds)`, `suspend()`, `on_camera_status(status: CameraStatus)`, `start_break_now()`, `snooze_break()`, `skip_break()`, property `is_paused -> bool`.
  - `build_coach(settings: Settings, clock: Clock, notifier: Notifier, idle: IdleTimeProvider) -> Coach`; `DEFAULT_OPEN_EAR = 0.28`; `DEFAULT_FOCAL_SCALE = 660.0`.
  - Fakes: `RecordingPolicy`, `RecordingBreakControl`. Integration helper `PipelineRun(settings=CALIBRATED_SETTINGS)` with `.clock`, `.notifier`, `.idle`, `.coach`, `play(*segments)`, `pass_time(seconds: int)`.

Tray status: paused or camera busy → `PAUSED`; camera unavailable → `NO_CAMERA`; otherwise `MONITORING`.

- [ ] **Step 1: Write the fakes and the pipeline harness**

`tests/fakes/policies.py`:

```python
from spare_my_eyes.capture.face_sample import FaceSample


class RecordingPolicy:
    def __init__(self) -> None:
        self.samples: list[FaceSample] = []
        self.ticks: list[float] = []
        self.suspensions = 0

    def on_sample(self, sample: FaceSample) -> None:
        self.samples.append(sample)

    def on_tick(self, now: float) -> None:
        self.ticks.append(now)

    def suspend(self) -> None:
        self.suspensions += 1


class RecordingBreakControl:
    def __init__(self) -> None:
        self.samples: list[FaceSample] = []
        self.ticks: list[tuple[float, float]] = []
        self.commands: list[str] = []
        self.camera_active = True

    def on_sample(self, sample: FaceSample) -> None:
        self.samples.append(sample)

    def on_tick(self, now: float, idle_seconds: float) -> None:
        self.ticks.append((now, idle_seconds))

    def start_now(self) -> None:
        self.commands.append("start_now")

    def snooze(self) -> None:
        self.commands.append("snooze")

    def skip(self) -> None:
        self.commands.append("skip")

    def suspend(self) -> None:
        self.commands.append("suspend")

    def use_camera(self) -> None:
        self.camera_active = True

    def use_idle_time(self) -> None:
        self.camera_active = False
```

`tests/integration/pipeline_run.py`:

```python
from spare_my_eyes.analysis.distance import ARM_LENGTH_CM
from spare_my_eyes.capture.scripted import DEFAULT_IRIS_DIAMETER_PX, OPEN_EAR, TimelineSegment
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.timeline import TimelineDriver

CALIBRATED_SETTINGS = Settings(
    open_ear_baseline=OPEN_EAR, focal_scale=DEFAULT_IRIS_DIAMETER_PX * ARM_LENGTH_CM
)
USER_NOT_TYPING_SECONDS = 10_000.0


class PipelineRun:
    """The real analyzers and Coach, driven by a scripted timeline on a fake clock."""

    def __init__(self, settings: Settings = CALIBRATED_SETTINGS) -> None:
        self.clock = FakeClock()
        self.notifier = RecordingNotifier()
        self.idle = FakeIdleTimeProvider(USER_NOT_TYPING_SECONDS)
        self.coach = build_coach(settings, self.clock, self.notifier, self.idle)
        self._driver = TimelineDriver(self.clock, self.coach.on_sample, self.coach.tick)

    def play(self, *segments: TimelineSegment) -> None:
        self._driver.play(*segments)

    def pass_time(self, seconds: int) -> None:
        self._driver.pass_time(seconds)
```

- [ ] **Step 2: Write the failing Coach unit tests**

`tests/unit/test_coach.py`:

```python
from dataclasses import dataclass

import pytest

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.coaching.coach import Coach
from spare_my_eyes.coaching.notifier import TrayStatus
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.policies import RecordingBreakControl, RecordingPolicy

SAMPLE = FaceSample(timestamp=0.0, face_present=True, left_ear=0.3, right_ear=0.3)


@dataclass
class CoachRig:
    coach: Coach
    policy: RecordingPolicy
    breaks: RecordingBreakControl
    notifier: RecordingNotifier
    clock: FakeClock


@pytest.fixture
def rig() -> CoachRig:
    clock = FakeClock()
    policy = RecordingPolicy()
    breaks = RecordingBreakControl()
    notifier = RecordingNotifier()
    coach = Coach([policy], breaks, lambda: 12.0, FakeIdleTimeProvider(4.0), notifier, clock)
    return CoachRig(coach, policy, breaks, notifier, clock)


def test_on_sample_forwards_to_policies_and_breaks(rig: CoachRig) -> None:
    rig.coach.on_sample(SAMPLE)
    assert rig.policy.samples == [SAMPLE]
    assert rig.breaks.samples == [SAMPLE]


def test_tick_forwards_time_and_idle_and_reports_monitoring(rig: CoachRig) -> None:
    rig.clock.advance(5.0)
    rig.coach.tick()
    assert rig.policy.ticks == [5.0]
    assert rig.breaks.ticks == [(5.0, 4.0)]
    assert rig.notifier.status is TrayStatus.MONITORING
    assert rig.notifier.blinks_per_minute == 12.0


def test_pause_for_suspends_everything_and_ignores_input(rig: CoachRig) -> None:
    rig.coach.pause_for(3600.0)
    rig.coach.on_sample(SAMPLE)
    rig.coach.tick()
    assert rig.policy.suspensions == 1
    assert "suspend" in rig.breaks.commands
    assert rig.policy.samples == []
    assert rig.policy.ticks == []
    assert rig.notifier.status is TrayStatus.PAUSED


def test_tick_after_pause_expires_resumes_monitoring(rig: CoachRig) -> None:
    rig.coach.pause_for(60.0)
    rig.clock.advance(60.0)
    rig.coach.tick()
    assert not rig.coach.is_paused
    assert rig.policy.ticks == [60.0]
    assert rig.notifier.status is TrayStatus.MONITORING


def test_on_camera_status_unavailable_switches_breaks_to_idle_time(rig: CoachRig) -> None:
    rig.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    assert rig.policy.suspensions == 1
    assert not rig.breaks.camera_active
    assert rig.notifier.status is TrayStatus.NO_CAMERA


def test_on_camera_status_busy_reports_paused(rig: CoachRig) -> None:
    rig.coach.on_camera_status(CameraStatus.BUSY)
    assert not rig.breaks.camera_active
    assert rig.notifier.status is TrayStatus.PAUSED


def test_on_camera_status_active_again_uses_camera(rig: CoachRig) -> None:
    rig.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    rig.coach.on_camera_status(CameraStatus.ACTIVE)
    assert rig.breaks.camera_active
    assert rig.notifier.status is TrayStatus.MONITORING


def test_break_commands_are_delegated(rig: CoachRig) -> None:
    rig.coach.start_break_now()
    rig.coach.snooze_break()
    rig.coach.skip_break()
    assert rig.breaks.commands == ["start_now", "snooze", "skip"]
```

- [ ] **Step 3: Write the failing pipeline scenarios**

`tests/integration/test_blink_nudge_pipeline.py`:

```python
from spare_my_eyes.capture.scripted import ScriptedBlink, TimelineSegment
from spare_my_eyes.coaching.blink_nudge import BLINK_MESSAGE, SLOW_BLINK_MESSAGE
from tests.integration.pipeline_run import PipelineRun

LOW_RATE = 4.8


def test_blink_nudge_low_rate_shows_then_two_complete_blinks_hide_it() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    assert run.notifier.blink_nudge == BLINK_MESSAGE
    run.play(TimelineSegment(0.5, blinks_per_minute=60.0))
    assert run.notifier.blink_nudge == BLINK_MESSAGE
    run.play(TimelineSegment(0.5, blinks_per_minute=60.0))
    assert run.notifier.blink_nudge is None


def test_blink_nudge_after_hiding_respects_three_minute_cooldown() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(121.0, blinks_per_minute=LOW_RATE))
    run.play(TimelineSegment(9.0, blinks_per_minute=0.0))
    assert run.notifier.blink_nudge is None
    run.play(TimelineSegment(170.0, blinks_per_minute=LOW_RATE))
    assert run.notifier.count("show_blink_nudge") == 1
    run.play(TimelineSegment(15.0, blinks_per_minute=LOW_RATE))
    assert run.notifier.count("show_blink_nudge") == 2


def test_blink_nudge_mostly_incomplete_blinks_ask_for_full_closure() -> None:
    run = PipelineRun()
    run.play(
        TimelineSegment(121.0, blinks_per_minute=LOW_RATE, blink=ScriptedBlink.INCOMPLETE)
    )
    assert run.notifier.blink_nudge == SLOW_BLINK_MESSAGE


def test_blink_nudge_normal_blinking_never_shows() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(600.0))
    assert run.notifier.count("show_blink_nudge") == 0
```

`tests/integration/test_distance_pipeline.py`:

```python
from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.distance_alert import MOVE_BACK_MESSAGE
from tests.integration.pipeline_run import CALIBRATED_SETTINGS, PipelineRun


def at_cm(duration: float, centimeters: float) -> TimelineSegment:
    assert CALIBRATED_SETTINGS.focal_scale is not None
    return TimelineSegment(duration, iris_diameter_px=CALIBRATED_SETTINGS.focal_scale / centimeters)


def test_distance_alert_shows_after_thirty_seconds_close_and_hides_past_55_cm() -> None:
    run = PipelineRun()
    run.play(at_cm(29.0, 45.0))
    assert run.notifier.distance_alert is None
    run.play(at_cm(2.0, 45.0))
    assert run.notifier.distance_alert == MOVE_BACK_MESSAGE
    run.play(at_cm(10.0, 52.0))
    assert run.notifier.distance_alert == MOVE_BACK_MESSAGE
    run.play(at_cm(5.0, 58.0))
    assert run.notifier.distance_alert is None


def test_distance_alert_respects_five_minute_cooldown() -> None:
    run = PipelineRun()
    run.play(at_cm(31.0, 45.0))
    run.play(at_cm(5.0, 58.0))
    run.play(at_cm(60.0, 45.0))
    assert run.notifier.distance_alert is None
    run.play(at_cm(250.0, 45.0))
    assert run.notifier.distance_alert == MOVE_BACK_MESSAGE
```

`tests/integration/test_break_pipeline.py`:

```python
from spare_my_eyes.capture.scripted import ScriptedBlink, TimelineSegment
from spare_my_eyes.coaching.break_session import BreakStep
from spare_my_eyes.coaching.notifier import TrayStatus
from tests.integration.pipeline_run import PipelineRun

TWENTY_MINUTES = 1200.0


def run_until_break() -> PipelineRun:
    run = PipelineRun()
    run.play(TimelineSegment(TWENTY_MINUTES + 2.0))
    return run


def test_break_twenty_minutes_of_presence_shows_break_card() -> None:
    progress = run_until_break().notifier.break_progress
    assert progress is not None
    assert progress.step is BreakStep.LOOK_OUT
    assert progress.verified


def test_break_gaze_and_slow_blinks_complete_it_and_reset_screen_time() -> None:
    run = run_until_break()
    run.play(TimelineSegment(21.0, head_yaw_degrees=-30.0))
    progress = run.notifier.break_progress
    assert progress is not None and progress.step is BreakStep.SLOW_BLINKS
    run.play(TimelineSegment(10.5, blinks_per_minute=30.0, blink=ScriptedBlink.SLOW))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(1150.0))
    assert run.notifier.break_progress is None


def test_break_looking_to_the_wrong_side_does_not_progress() -> None:
    run = run_until_break()
    run.play(TimelineSegment(21.0, head_yaw_degrees=30.0))
    progress = run.notifier.break_progress
    assert progress is not None
    assert progress.gaze_seconds == 0.0


def test_break_snooze_brings_card_back_after_five_minutes() -> None:
    run = run_until_break()
    run.coach.snooze_break()
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(298.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(4.0))
    assert run.notifier.break_progress is not None


def test_break_skip_hides_card_and_resets_screen_time() -> None:
    run = run_until_break()
    run.coach.skip_break()
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(1150.0))
    assert run.notifier.break_progress is None


def test_break_two_minutes_without_interaction_times_out() -> None:
    run = run_until_break()
    run.play(TimelineSegment(123.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(1100.0))
    assert run.notifier.break_progress is None


def test_break_short_absence_pauses_screen_time() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(600.0))
    run.play(TimelineSegment(240.0, face_present=False))
    run.play(TimelineSegment(530.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(15.0))
    assert run.notifier.break_progress is not None


def test_break_absence_of_five_minutes_resets_screen_time() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(600.0))
    run.play(TimelineSegment(301.0, face_present=False))
    run.play(TimelineSegment(1190.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(15.0))
    assert run.notifier.break_progress is not None


def test_break_sleep_gap_resets_screen_time() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(600.0))
    run.clock.advance(3600.0)
    run.play(TimelineSegment(1190.0))
    assert run.notifier.break_progress is None
    run.play(TimelineSegment(15.0))
    assert run.notifier.break_progress is not None


def test_break_face_never_detected_but_user_typing_still_gets_unverified_break() -> None:
    run = PipelineRun()
    run.idle.seconds = 0.0
    run.play(TimelineSegment(TWENTY_MINUTES + 2.0, face_present=False))
    progress = run.notifier.break_progress
    assert progress is not None
    assert not progress.verified


def test_pause_hides_open_break_card() -> None:
    run = run_until_break()
    run.coach.pause_for(3600.0)
    assert run.notifier.break_progress is None
    assert run.notifier.status is TrayStatus.PAUSED
```

`tests/integration/test_camera_fallback_pipeline.py`:

```python
from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.notifier import TrayStatus
from tests.integration.pipeline_run import PipelineRun


def test_camera_unavailable_reports_no_camera_and_keeps_time_based_breaks() -> None:
    run = PipelineRun()
    run.idle.seconds = 0.0
    run.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    assert run.notifier.status is TrayStatus.NO_CAMERA
    run.pass_time(1202)
    progress = run.notifier.break_progress
    assert progress is not None and not progress.verified
    run.idle.seconds = 10.0
    run.pass_time(32)
    assert run.notifier.break_progress is None


def test_camera_busy_pauses_measurement_and_keeps_time_based_breaks() -> None:
    run = PipelineRun()
    run.idle.seconds = 0.0
    run.coach.on_camera_status(CameraStatus.BUSY)
    run.pass_time(1202)
    assert run.notifier.status is TrayStatus.PAUSED
    progress = run.notifier.break_progress
    assert progress is not None and not progress.verified


def test_camera_unplugged_hides_visible_blink_nudge() -> None:
    run = PipelineRun()
    run.play(TimelineSegment(121.0, blinks_per_minute=4.8))
    assert run.notifier.blink_nudge is not None
    run.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    assert run.notifier.blink_nudge is None


def test_camera_back_reports_monitoring() -> None:
    run = PipelineRun()
    run.coach.on_camera_status(CameraStatus.UNAVAILABLE)
    run.coach.on_camera_status(CameraStatus.ACTIVE)
    assert run.notifier.status is TrayStatus.MONITORING
```

- [ ] **Step 4: Run to see them fail**

Run: `uv run pytest tests/unit/test_coach.py tests/integration -v -k "not windows_idle"`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.coaching.coach'` (and `... factory`).

- [ ] **Step 5: Implement the Coach**

`src/spare_my_eyes/coaching/coach.py`:

```python
from collections.abc import Callable, Sequence
from typing import Protocol

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.notifier import Notifier, TrayStatus
from spare_my_eyes.system.idle_time import IdleTimeProvider


class CoachingPolicy(Protocol):
    def on_sample(self, sample: FaceSample) -> None: ...

    def on_tick(self, now: float) -> None: ...

    def suspend(self) -> None: ...


class BreakControl(Protocol):
    def on_sample(self, sample: FaceSample) -> None: ...

    def on_tick(self, now: float, idle_seconds: float) -> None: ...

    def start_now(self) -> None: ...

    def snooze(self) -> None: ...

    def skip(self) -> None: ...

    def suspend(self) -> None: ...

    def use_camera(self) -> None: ...

    def use_idle_time(self) -> None: ...


class Coach:
    """Feeds samples and ticks to the coaching policies and reports the tray status."""

    def __init__(
        self,
        camera_policies: Sequence[CoachingPolicy],
        breaks: BreakControl,
        blink_rate: Callable[[], float | None],
        idle: IdleTimeProvider,
        notifier: Notifier,
        clock: Clock,
    ) -> None:
        self._camera_policies = tuple(camera_policies)
        self._breaks = breaks
        self._blink_rate = blink_rate
        self._idle = idle
        self._notifier = notifier
        self._clock = clock
        self._camera_status = CameraStatus.ACTIVE
        self._paused_until: float | None = None

    @property
    def is_paused(self) -> bool:
        return self._paused_until is not None

    def on_sample(self, sample: FaceSample) -> None:
        if self.is_paused:
            return
        for policy in self._camera_policies:
            policy.on_sample(sample)
        self._breaks.on_sample(sample)

    def tick(self) -> None:
        now = self._clock.now()
        self._resume_when_due(now)
        if not self.is_paused:
            self._tick_policies(now)
        self._report_status()

    def pause_for(self, seconds: float) -> None:
        self._paused_until = self._clock.now() + seconds
        self.suspend()
        self._report_status()

    def suspend(self) -> None:
        self._suspend_camera_policies()
        self._breaks.suspend()

    def on_camera_status(self, status: CameraStatus) -> None:
        self._camera_status = status
        if status is CameraStatus.ACTIVE:
            self._breaks.use_camera()
        else:
            self._suspend_camera_policies()
            self._breaks.use_idle_time()
        self._report_status()

    def start_break_now(self) -> None:
        self._paused_until = None
        self._breaks.start_now()

    def snooze_break(self) -> None:
        self._breaks.snooze()

    def skip_break(self) -> None:
        self._breaks.skip()

    def _tick_policies(self, now: float) -> None:
        for policy in self._camera_policies:
            policy.on_tick(now)
        self._breaks.on_tick(now, self._idle.idle_seconds())

    def _resume_when_due(self, now: float) -> None:
        if self._paused_until is not None and now >= self._paused_until:
            self._paused_until = None

    def _suspend_camera_policies(self) -> None:
        for policy in self._camera_policies:
            policy.suspend()

    def _status(self) -> TrayStatus:
        if self.is_paused or self._camera_status is CameraStatus.BUSY:
            return TrayStatus.PAUSED
        if self._camera_status is CameraStatus.UNAVAILABLE:
            return TrayStatus.NO_CAMERA
        return TrayStatus.MONITORING

    def _report_status(self) -> None:
        self._notifier.set_status(self._status(), self._blink_rate())
```

- [ ] **Step 6: Implement build_coach**

`src/spare_my_eyes/coaching/factory.py`:

```python
from spare_my_eyes.analysis.blink_detector import BlinkDetector
from spare_my_eyes.analysis.blink_rate import BlinkRateMonitor
from spare_my_eyes.analysis.distance import DistanceThresholds, ScreenDistanceEstimator
from spare_my_eyes.analysis.gaze import WindowGazeDetector
from spare_my_eyes.analysis.presence import PresenceTracker
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.blink_nudge import BlinkNudgePolicy, BlinkNudgeRules
from spare_my_eyes.coaching.break_policy import BreakPolicy, BreakSchedule
from spare_my_eyes.coaching.break_session import BreakTargets
from spare_my_eyes.coaching.coach import Coach
from spare_my_eyes.coaching.cooldown import Cooldown
from spare_my_eyes.coaching.distance_alert import DistanceAlertPolicy
from spare_my_eyes.coaching.notifier import Notifier
from spare_my_eyes.settings import Settings
from spare_my_eyes.system.idle_time import IdleTimeProvider

DEFAULT_OPEN_EAR = 0.28
DEFAULT_FOCAL_SCALE = 660.0


def build_coach(
    settings: Settings, clock: Clock, notifier: Notifier, idle: IdleTimeProvider
) -> Coach:
    baseline = settings.open_ear_baseline or DEFAULT_OPEN_EAR
    nudge = _blink_nudge_policy(settings, baseline, notifier)
    distance = _distance_alert_policy(settings, notifier)
    breaks = _break_policy(settings, baseline, notifier, clock)
    return Coach([nudge, distance], breaks, nudge.current_rate, idle, notifier, clock)


def _blink_nudge_policy(
    settings: Settings, baseline: float, notifier: Notifier
) -> BlinkNudgePolicy:
    rules = BlinkNudgeRules(
        rate_threshold_per_minute=settings.blink_rate_threshold_per_minute,
        incomplete_ratio_threshold=settings.incomplete_ratio_threshold,
        max_visible_seconds=settings.nudge_max_seconds,
        hide_after_complete_blinks=settings.nudge_hide_after_complete_blinks,
        cooldown_seconds=settings.nudge_cooldown_seconds,
    )
    monitor = BlinkRateMonitor(settings.blink_window_seconds)
    return BlinkNudgePolicy(BlinkDetector(baseline), monitor, rules, notifier)


def _distance_alert_policy(settings: Settings, notifier: Notifier) -> DistanceAlertPolicy:
    thresholds = DistanceThresholds(
        too_close_cm=settings.too_close_cm,
        clear_cm=settings.distance_clear_cm,
        hold_seconds=settings.distance_hold_seconds,
    )
    focal_scale = settings.focal_scale or DEFAULT_FOCAL_SCALE
    estimator = ScreenDistanceEstimator(focal_scale, thresholds)
    return DistanceAlertPolicy(estimator, Cooldown(settings.distance_cooldown_seconds), notifier)


def _break_policy(
    settings: Settings, baseline: float, notifier: Notifier, clock: Clock
) -> BreakPolicy:
    schedule = BreakSchedule(
        interval_seconds=settings.break_interval_seconds,
        snooze_seconds=settings.snooze_seconds,
        absence_reset_seconds=settings.absence_reset_seconds,
    )
    targets = BreakTargets(
        gaze_seconds=settings.break_gaze_seconds,
        slow_blinks=settings.break_slow_blinks,
        slow_blink_min_seconds=settings.slow_blink_min_seconds,
        inactivity_timeout_seconds=settings.break_inactivity_timeout_seconds,
    )
    gaze = WindowGazeDetector(settings.window_side, settings.break_min_yaw_degrees)
    presence = PresenceTracker(settings.absent_after_seconds)
    return BreakPolicy(schedule, targets, gaze, presence, baseline, notifier, clock)
```

- [ ] **Step 7: Run to see them pass**

Run: `uv run pytest tests/unit/test_coach.py tests/integration -v && uv run mypy`
Expected: all passed, mypy clean. The pipeline suite replays about an hour of simulated time; it should finish in a few seconds. If one scenario fails, debug it with superpowers:systematic-debugging before touching thresholds; the numbers in the tests come from the spec.

- [ ] **Step 8: Commit**

```bash
git add src/spare_my_eyes/coaching/coach.py src/spare_my_eyes/coaching/factory.py tests/fakes/policies.py tests/integration/pipeline_run.py tests/unit/test_coach.py tests/integration/test_blink_nudge_pipeline.py tests/integration/test_distance_pipeline.py tests/integration/test_break_pipeline.py tests/integration/test_camera_fallback_pipeline.py
git commit -m "feat: compose coaching policies into a Coach with pipeline scenarios

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 17: EyeCareController (calibration before monitoring)

**Files:**
- Create: `src/spare_my_eyes/coaching/controller.py`
- Test: `tests/unit/test_controller.py`, `tests/integration/test_calibration_pipeline.py`

**Interfaces:**
- Consumes: `CalibrationSession`, `CalibrationResult` (Task 9), `Coach`, `build_coach` (Task 16), `SettingsStore`, `Settings` (Task 8), `CameraStatus`, `Notifier`, `TrayStatus`, `log_event`.
- Produces: `EyeCareController(settings: Settings, store: SettingsStore, coach_factory: Callable[[Settings], Coach], notifier: Notifier, clock: Clock, logger: logging.Logger)` with `on_sample(sample)`, `tick()`, `on_camera_status(status)`, `recalibrate()`, `pause_for(seconds)`, `start_break_now()`, `snooze_break()`, `skip_break()`; properties `settings -> Settings`, `is_paused -> bool`, `is_calibrating -> bool`. Logs `calibration_completed`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_controller.py`:

```python
from dataclasses import dataclass, replace
from functools import partial

import pytest

from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.settings_store import InMemorySettingsStore
from tests.fakes.timeline import TimelineDriver
from tests.integration.pipeline_run import CALIBRATED_SETTINGS


@dataclass
class ControllerRig:
    controller: EyeCareController
    notifier: RecordingNotifier
    store: InMemorySettingsStore
    driver: TimelineDriver


def make_rig(settings: Settings, log_recorder: RecordingLogHandler) -> ControllerRig:
    clock = FakeClock()
    notifier = RecordingNotifier()
    store = InMemorySettingsStore(settings)
    factory = partial(
        build_coach, clock=clock, notifier=notifier, idle=FakeIdleTimeProvider(10_000.0)
    )
    controller = EyeCareController(
        settings, store, factory, notifier, clock, log_recorder.logger
    )
    driver = TimelineDriver(clock, controller.on_sample, controller.tick)
    return ControllerRig(controller, notifier, store, driver)


@pytest.fixture
def first_launch(log_recorder: RecordingLogHandler) -> ControllerRig:
    return make_rig(Settings(), log_recorder)


def test_init_uncalibrated_starts_calibration(first_launch: ControllerRig) -> None:
    assert first_launch.controller.is_calibrating
    assert first_launch.notifier.status is TrayStatus.CALIBRATING
    assert first_launch.notifier.calibration is not None


def test_on_sample_twenty_seconds_of_face_saves_calibration(
    first_launch: ControllerRig, log_recorder: RecordingLogHandler
) -> None:
    first_launch.driver.play(TimelineSegment(20.5))
    saved = first_launch.store.saved[-1]
    assert saved.open_ear_baseline == pytest.approx(0.30)
    assert saved.focal_scale == pytest.approx(660.0)
    assert not first_launch.controller.is_calibrating
    assert first_launch.notifier.calibration is None
    assert "calibration_completed" in log_recorder.events()


def test_on_sample_calibrated_start_goes_straight_to_coaching(
    log_recorder: RecordingLogHandler,
) -> None:
    rig = make_rig(CALIBRATED_SETTINGS, log_recorder)
    rig.driver.play(TimelineSegment(121.0, blinks_per_minute=4.8))
    assert rig.notifier.count("show_calibration") == 0
    assert rig.notifier.blink_nudge is not None


def test_on_camera_status_unavailable_cancels_and_active_restarts_calibration(
    first_launch: ControllerRig,
) -> None:
    first_launch.controller.on_camera_status(CameraStatus.UNAVAILABLE)
    assert not first_launch.controller.is_calibrating
    assert first_launch.notifier.calibration is None
    first_launch.controller.on_camera_status(CameraStatus.ACTIVE)
    assert first_launch.controller.is_calibrating


def test_recalibrate_hides_open_break_and_shows_calibration(
    log_recorder: RecordingLogHandler,
) -> None:
    rig = make_rig(replace(CALIBRATED_SETTINGS, break_interval_seconds=2.0), log_recorder)
    rig.driver.play(TimelineSegment(4.0))
    assert rig.notifier.break_progress is not None
    rig.controller.recalibrate()
    assert rig.notifier.break_progress is None
    assert rig.notifier.calibration is not None


def test_pause_for_during_calibration_cancels_it(first_launch: ControllerRig) -> None:
    first_launch.controller.pause_for(3600.0)
    assert not first_launch.controller.is_calibrating
    assert first_launch.controller.is_paused
```

`tests/integration/test_calibration_pipeline.py`:

```python
from functools import partial

from spare_my_eyes.capture.scripted import TimelineSegment
from spare_my_eyes.coaching.blink_nudge import BLINK_MESSAGE
from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.settings_store import InMemorySettingsStore
from tests.fakes.timeline import TimelineDriver


def test_first_launch_calibrates_then_nudges_on_low_blink_rate(
    log_recorder: RecordingLogHandler,
) -> None:
    clock = FakeClock()
    notifier = RecordingNotifier()
    factory = partial(
        build_coach, clock=clock, notifier=notifier, idle=FakeIdleTimeProvider(10_000.0)
    )
    controller = EyeCareController(
        Settings(), InMemorySettingsStore(), factory, notifier, clock, log_recorder.logger
    )
    driver = TimelineDriver(clock, controller.on_sample, controller.tick)
    driver.play(TimelineSegment(21.0))
    assert controller.settings.is_calibrated
    driver.play(TimelineSegment(121.0, blinks_per_minute=4.8))
    assert notifier.blink_nudge == BLINK_MESSAGE
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_controller.py tests/integration/test_calibration_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.coaching.controller'`.

- [ ] **Step 3: Implement**

`src/spare_my_eyes/coaching/controller.py`:

```python
import logging
from collections.abc import Callable
from dataclasses import replace

from spare_my_eyes.calibration import CalibrationResult, CalibrationSession
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.coach import Coach
from spare_my_eyes.coaching.notifier import Notifier, TrayStatus
from spare_my_eyes.settings import Settings
from spare_my_eyes.settings_store import SettingsStore
from spare_my_eyes.structured_log import log_event


class EyeCareController:
    """Runs calibration until the user is calibrated, then hands samples to the Coach."""

    def __init__(
        self,
        settings: Settings,
        store: SettingsStore,
        coach_factory: Callable[[Settings], Coach],
        notifier: Notifier,
        clock: Clock,
        logger: logging.Logger,
    ) -> None:
        self._settings = settings
        self._store = store
        self._coach_factory = coach_factory
        self._notifier = notifier
        self._clock = clock
        self._logger = logger
        self._coach = coach_factory(settings)
        self._calibration: CalibrationSession | None = None
        if not settings.is_calibrated:
            self.recalibrate()

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def is_paused(self) -> bool:
        return self._coach.is_paused

    @property
    def is_calibrating(self) -> bool:
        return self._calibration is not None

    def recalibrate(self) -> None:
        self._coach.suspend()
        now = self._clock.now()
        self._calibration = CalibrationSession(now)
        self._notifier.set_status(TrayStatus.CALIBRATING, None)
        self._notifier.show_calibration(self._calibration.progress(now))

    def on_sample(self, sample: FaceSample) -> None:
        if self._calibration is None:
            self._coach.on_sample(sample)
            return
        progress = self._calibration.update(sample)
        result = self._calibration.result
        if result is None:
            self._notifier.show_calibration(progress)
            return
        self._finish_calibration(result)

    def tick(self) -> None:
        if self._calibration is None:
            self._coach.tick()

    def on_camera_status(self, status: CameraStatus) -> None:
        self._coach.on_camera_status(status)
        if status is not CameraStatus.ACTIVE:
            self._cancel_calibration()
            return
        if not self._settings.is_calibrated and self._calibration is None:
            self.recalibrate()

    def pause_for(self, seconds: float) -> None:
        self._cancel_calibration()
        self._coach.pause_for(seconds)

    def start_break_now(self) -> None:
        if self._calibration is None:
            self._coach.start_break_now()

    def snooze_break(self) -> None:
        self._coach.snooze_break()

    def skip_break(self) -> None:
        self._coach.skip_break()

    def _cancel_calibration(self) -> None:
        if self._calibration is None:
            return
        self._calibration = None
        self._notifier.hide_calibration()

    def _finish_calibration(self, result: CalibrationResult) -> None:
        self._settings = replace(
            self._settings,
            open_ear_baseline=result.open_ear_baseline,
            focal_scale=result.focal_scale,
        )
        self._store.save(self._settings)
        self._calibration = None
        self._notifier.hide_calibration()
        self._coach = self._coach_factory(self._settings)
        log_event(
            self._logger,
            logging.INFO,
            "calibration_completed",
            open_ear_baseline=result.open_ear_baseline,
            focal_scale=result.focal_scale,
        )
```

- [ ] **Step 4: Run to see them pass**

Run: `uv run pytest tests/unit/test_controller.py tests/integration/test_calibration_pipeline.py -v && uv run mypy`
Expected: 7 passed, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/spare_my_eyes/coaching/controller.py tests/unit/test_controller.py tests/integration/test_calibration_pipeline.py
git commit -m "feat: run calibration before monitoring and persist the result

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 18: FrameSource and OpenCvFrameSource

**Files:**
- Create: `src/spare_my_eyes/capture/frame_source.py`, `src/spare_my_eyes/capture/opencv_frame_source.py`
- Create: `tests/fakes/frame_sources.py`
- Test: `tests/integration/test_opencv_frame_source.py`

**Interfaces:**
- Consumes: `CameraUnavailableError`, `CameraBusyError` (Task 12).
- Produces:
  - `Frame = npt.NDArray[np.uint8]` (BGR, height × width × 3).
  - `FrameSource` protocol: `open() -> None`, `read() -> Frame`, `close() -> None` (idempotent).
  - `OpenCvFrameSource(camera_index: int, width: int = 640, height: int = 480, fps: float = 20.0)`. A failed open raises `CameraUnavailableError`; an open camera that returns no frame raises `CameraBusyError`.
  - Fakes: `FailingFrameSource(open_error: Exception | None = None, read_error: Exception | None = None)` with `open_calls`, `close_calls`; `StillImageFrameSource(frame: Frame)` returning a copy on every read.

- [ ] **Step 1: Write the fakes**

`tests/fakes/frame_sources.py`:

```python
import numpy as np

from spare_my_eyes.capture.frame_source import Frame


class FailingFrameSource:
    def __init__(
        self, open_error: Exception | None = None, read_error: Exception | None = None
    ) -> None:
        self._open_error = open_error
        self._read_error = read_error
        self.open_calls = 0
        self.close_calls = 0

    def open(self) -> None:
        self.open_calls += 1
        if self._open_error is not None:
            raise self._open_error

    def read(self) -> Frame:
        if self._read_error is not None:
            raise self._read_error
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def close(self) -> None:
        self.close_calls += 1


class StillImageFrameSource:
    def __init__(self, frame: Frame) -> None:
        self._frame = frame

    def open(self) -> None:
        return None

    def read(self) -> Frame:
        return self._frame.copy()

    def close(self) -> None:
        return None
```

- [ ] **Step 2: Write the failing tests**

`tests/integration/test_opencv_frame_source.py`:

```python
import pytest

from spare_my_eyes.capture.camera_errors import CameraUnavailableError
from spare_my_eyes.capture.opencv_frame_source import OpenCvFrameSource

MISSING_CAMERA_INDEX = 99


def test_open_missing_camera_index_raises_camera_unavailable() -> None:
    with pytest.raises(CameraUnavailableError, match=str(MISSING_CAMERA_INDEX)):
        OpenCvFrameSource(MISSING_CAMERA_INDEX).open()


def test_read_before_open_raises_camera_unavailable() -> None:
    with pytest.raises(CameraUnavailableError, match="before open"):
        OpenCvFrameSource(0).read()


def test_close_without_open_does_nothing() -> None:
    OpenCvFrameSource(0).close()
```

- [ ] **Step 3: Run to see them fail**

Run: `uv run pytest tests/integration/test_opencv_frame_source.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.capture.opencv_frame_source'`.

- [ ] **Step 4: Implement**

`src/spare_my_eyes/capture/frame_source.py`:

```python
from typing import Protocol

import numpy as np
import numpy.typing as npt

Frame = npt.NDArray[np.uint8]


class FrameSource(Protocol):
    def open(self) -> None: ...

    def read(self) -> Frame: ...

    def close(self) -> None: ...
```

`src/spare_my_eyes/capture/opencv_frame_source.py`:

```python
import cv2
import numpy as np

from spare_my_eyes.capture.camera_errors import CameraBusyError, CameraUnavailableError
from spare_my_eyes.capture.frame_source import Frame


class OpenCvFrameSource:
    def __init__(
        self, camera_index: int, width: int = 640, height: int = 480, fps: float = 20.0
    ) -> None:
        self._camera_index = camera_index
        self._width = width
        self._height = height
        self._fps = fps
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        capture = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            raise CameraUnavailableError(
                f"Camera {self._camera_index} could not be opened; "
                "expected a connected webcam at that index"
            )
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        capture.set(cv2.CAP_PROP_FPS, self._fps)
        self._capture = capture

    def read(self) -> Frame:
        if self._capture is None:
            raise CameraUnavailableError(f"Camera {self._camera_index} was read before open()")
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise CameraBusyError(
                f"Camera {self._camera_index} is open but returned no frame; "
                "another app may be using it"
            )
        return np.asarray(frame, dtype=np.uint8)

    def close(self) -> None:
        if self._capture is None:
            return
        self._capture.release()
        self._capture = None
```

- [ ] **Step 5: Run to see them pass**

Run: `uv run pytest tests/integration/test_opencv_frame_source.py -v && uv run mypy`
Expected: 3 passed, mypy clean.

- [ ] **Step 6: Commit**

```bash
git add src/spare_my_eyes/capture/frame_source.py src/spare_my_eyes/capture/opencv_frame_source.py tests/fakes/frame_sources.py tests/integration/test_opencv_frame_source.py
git commit -m "feat: read webcam frames through an OpenCV adapter

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 19: Model download and MediaPipeFaceLandmarker

**Files:**
- Create: `src/spare_my_eyes/model_asset.py`, `src/spare_my_eyes/assets/.gitkeep`
- Create: `src/spare_my_eyes/capture/landmarker.py`, `src/spare_my_eyes/capture/mediapipe_landmarker.py`
- Create: `tests/integration/face_images.py`, `tests/fixtures/CREDITS.md`, `tests/fixtures/faces/*.jpg`
- Test: `tests/unit/test_model_asset.py`, `tests/integration/test_mediapipe_landmarker.py`

**Interfaces:**
- Consumes: `FaceSample` (Task 2), geometry (Task 3), `Frame` (Task 18).
- Produces:
  - `MODEL_URL`, `MODEL_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"` (float16 v1, 3,758,596 bytes, verified on 2026-10-15), `MODEL_PATH = <package>/assets/face_landmarker.task`, `ModelIntegrityError`, `sha256_of(path) -> str`, `verify_model(path, expected_sha256=MODEL_SHA256) -> None`, `download_model(destination=MODEL_PATH, url=MODEL_URL, expected_sha256=MODEL_SHA256) -> None`. `python -m spare_my_eyes.model_asset` downloads it.
  - `FaceLandmarkDetector` protocol: `detect(frame: Frame, timestamp: float) -> FaceSample`, `close() -> None`.
  - `MediaPipeFaceLandmarker(model_path: Path)`: raises `FileNotFoundError` naming the path and the download command when the model is missing.
  - Test helpers in `tests/integration/face_images.py`: `load_face(name) -> Frame` (skips when the fixture is absent), `blank_frame() -> Frame`, `shrink_into_canvas(frame, factor) -> Frame`, `detect_once(frame) -> FaceSample`.

The model is loaded from bytes (`model_asset_buffer`), so a Windows user name with non-ASCII characters in the path does not break MediaPipe.

- [ ] **Step 1: Write the failing model-asset tests**

`tests/unit/test_model_asset.py`:

```python
import hashlib
from pathlib import Path

import pytest

from spare_my_eyes.model_asset import ModelIntegrityError, download_model, verify_model

CONTENT = b"model-bytes"
CONTENT_SHA256 = hashlib.sha256(CONTENT).hexdigest()


def write_source(tmp_path: Path) -> Path:
    source = tmp_path / "source.task"
    source.write_bytes(CONTENT)
    return source


def test_download_model_matching_hash_writes_destination(tmp_path: Path) -> None:
    destination = tmp_path / "assets" / "face_landmarker.task"
    download_model(destination, write_source(tmp_path).as_uri(), CONTENT_SHA256)
    assert destination.read_bytes() == CONTENT


def test_download_model_wrong_hash_raises_and_leaves_nothing(tmp_path: Path) -> None:
    destination = tmp_path / "assets" / "face_landmarker.task"
    with pytest.raises(ModelIntegrityError, match="expected"):
        download_model(destination, write_source(tmp_path).as_uri(), "0" * 64)
    assert not destination.exists()
    assert not destination.with_suffix(".download").exists()


def test_download_model_already_present_does_not_download(tmp_path: Path) -> None:
    destination = tmp_path / "face_landmarker.task"
    destination.write_bytes(CONTENT)
    unreachable = (tmp_path / "missing.task").as_uri()
    download_model(destination, unreachable, CONTENT_SHA256)
    assert destination.read_bytes() == CONTENT


def test_verify_model_mismatched_file_raises_with_both_hashes(tmp_path: Path) -> None:
    with pytest.raises(ModelIntegrityError, match=CONTENT_SHA256):
        verify_model(write_source(tmp_path), "f" * 64)
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_model_asset.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.model_asset'`.

- [ ] **Step 3: Implement the model asset module**

`src/spare_my_eyes/model_asset.py`:

```python
import hashlib
import os
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
MODEL_PATH = Path(__file__).parent / "assets" / "face_landmarker.task"
_CHUNK_BYTES = 1 << 20


class ModelIntegrityError(Exception):
    pass


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model(path: Path, expected_sha256: str = MODEL_SHA256) -> None:
    actual = sha256_of(path)
    if actual != expected_sha256:
        raise ModelIntegrityError(f"{path} has SHA-256 {actual}; expected {expected_sha256}")


def download_model(
    destination: Path = MODEL_PATH, url: str = MODEL_URL, expected_sha256: str = MODEL_SHA256
) -> None:
    if destination.is_file() and sha256_of(destination) == expected_sha256:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".download")
    urllib.request.urlretrieve(url, temporary)
    try:
        verify_model(temporary, expected_sha256)
    except ModelIntegrityError:
        temporary.unlink()
        raise
    os.replace(temporary, destination)


def main() -> None:
    download_model()
    print(f"Face landmarker model ready at {MODEL_PATH}")


if __name__ == "__main__":
    main()
```

Create the empty file `src/spare_my_eyes/assets/.gitkeep`.

- [ ] **Step 4: Run, then download the real model**

```bash
uv run pytest tests/unit/test_model_asset.py -v
uv run python -m spare_my_eyes.model_asset
```

Expected: 4 passed; then `Face landmarker model ready at ...\src\spare_my_eyes\assets\face_landmarker.task`. The download is free (~3.8 MB).

- [ ] **Step 5: Add face fixture images**

Find three photos on Wikimedia Commons (https://commons.wikimedia.org) whose license is **CC0** or **Public domain**. Use the license filter in search and open each file page to confirm. Do not use the author's own face. Save them, scaled to about 640 px wide, as:

| File | Content |
|---|---|
| `tests/fixtures/faces/frontal_eyes_open.jpg` | One adult face, frontal, eyes open, face ≥ 200 px wide |
| `tests/fixtures/faces/frontal_eyes_closed.jpg` | One adult face, frontal, eyes fully closed |
| `tests/fixtures/faces/head_turned_left.jpg` | One face turned ~30–45° to the subject's own left (nose points toward the right edge of the image) |

Write `tests/fixtures/CREDITS.md`:

```markdown
# Test fixture credits

Every image here is public domain or CC0. Each row links to the file page that states the license.

| File | Source | Author | License |
|---|---|---|---|
| faces/frontal_eyes_open.jpg | <Commons file page URL> | <author> | <CC0 / Public domain> |
| faces/frontal_eyes_closed.jpg | <Commons file page URL> | <author> | <CC0 / Public domain> |
| faces/head_turned_left.jpg | <Commons file page URL> | <author> | <CC0 / Public domain> |

Derived cases generated in code, no extra files:
- head turned right = horizontal flip of `head_turned_left.jpg`
- face far away = `frontal_eyes_open.jpg` shrunk to half size on a gray canvas
- no face = a plain gray frame

## Missing cases

If no suitable CC0 image exists for a row, delete that row, list it here, and leave the file
out. The test that needs it is skipped with a message that points to this file.
```

Replace each `<...>` with the real values for the image you downloaded. A row without a real URL and license does not go in.

- [ ] **Step 6: Write the failing landmarker tests**

`tests/integration/face_images.py`:

```python
from pathlib import Path

import cv2
import numpy as np
import pytest

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.frame_source import Frame
from spare_my_eyes.capture.mediapipe_landmarker import MediaPipeFaceLandmarker
from spare_my_eyes.model_asset import MODEL_PATH

FACES_DIR = Path(__file__).parent.parent / "fixtures" / "faces"
FRAME_WIDTH = 640


def load_face(name: str) -> Frame:
    path = FACES_DIR / name
    if not path.is_file():
        pytest.skip(f"Fixture {name} is missing; see tests/fixtures/CREDITS.md")
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"{path} is not a readable image; expected a JPEG or PNG file")
    scale = FRAME_WIDTH / image.shape[1]
    resized = cv2.resize(image, (FRAME_WIDTH, round(image.shape[0] * scale)))
    return np.asarray(resized, dtype=np.uint8)


def blank_frame() -> Frame:
    return np.full((480, FRAME_WIDTH, 3), 128, dtype=np.uint8)


def shrink_into_canvas(frame: Frame, factor: float) -> Frame:
    small = cv2.resize(frame, None, fx=factor, fy=factor)
    canvas = np.full_like(frame, 128)
    canvas[: small.shape[0], : small.shape[1]] = small
    return canvas


def detect_once(frame: Frame) -> FaceSample:
    if not MODEL_PATH.is_file():
        pytest.fail(
            f"Model missing at {MODEL_PATH}; "
            "run `uv run python -m spare_my_eyes.model_asset`"
        )
    landmarker = MediaPipeFaceLandmarker(MODEL_PATH)
    try:
        return landmarker.detect(frame, 0.0)
    finally:
        landmarker.close()
```

`tests/integration/test_mediapipe_landmarker.py`:

```python
from pathlib import Path

import cv2
import numpy as np
import pytest

from spare_my_eyes.capture.mediapipe_landmarker import MediaPipeFaceLandmarker
from tests.integration.face_images import blank_frame, detect_once, load_face, shrink_into_canvas

pytestmark = pytest.mark.mediapipe


def test_detect_frontal_open_eyes_reports_open_ear_and_small_yaw() -> None:
    sample = detect_once(load_face("frontal_eyes_open.jpg"))
    assert sample.face_present
    assert 0.18 <= sample.mean_ear <= 0.45
    assert abs(sample.head_yaw_degrees) < 12.0
    assert sample.iris_diameter_px > 0.0


def test_detect_closed_eyes_reports_low_ear() -> None:
    sample = detect_once(load_face("frontal_eyes_closed.jpg"))
    assert sample.face_present
    assert sample.mean_ear < 0.15


def test_detect_head_turned_left_reports_negative_yaw() -> None:
    sample = detect_once(load_face("head_turned_left.jpg"))
    assert sample.face_present
    assert sample.head_yaw_degrees <= -15.0


def test_detect_head_turned_right_reports_positive_yaw() -> None:
    mirrored = np.ascontiguousarray(cv2.flip(load_face("head_turned_left.jpg"), 1))
    sample = detect_once(mirrored)
    assert sample.face_present
    assert sample.head_yaw_degrees >= 15.0


def test_detect_face_farther_away_reports_smaller_iris() -> None:
    near_frame = load_face("frontal_eyes_open.jpg")
    near = detect_once(near_frame)
    far = detect_once(shrink_into_canvas(near_frame, 0.5))
    assert far.face_present
    assert far.iris_diameter_px < near.iris_diameter_px * 0.7


def test_detect_blank_frame_reports_no_face() -> None:
    assert not detect_once(blank_frame()).face_present


def test_init_missing_model_raises_file_not_found_with_command(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="spare_my_eyes.model_asset"):
        MediaPipeFaceLandmarker(tmp_path / "missing.task")
```

- [ ] **Step 7: Run to see them fail**

Run: `uv run pytest tests/integration/test_mediapipe_landmarker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.capture.mediapipe_landmarker'`.

- [ ] **Step 8: Implement the landmarker**

`src/spare_my_eyes/capture/landmarker.py`:

```python
from typing import Protocol

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.frame_source import Frame


class FaceLandmarkDetector(Protocol):
    def detect(self, frame: Frame, timestamp: float) -> FaceSample: ...

    def close(self) -> None: ...
```

`src/spare_my_eyes/capture/mediapipe_landmarker.py`:

```python
from collections.abc import Sequence
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.frame_source import Frame
from spare_my_eyes.capture.geometry import Point, eye_aspect_ratio, iris_diameter, yaw_degrees

RIGHT_EYE = (33, 160, 158, 133, 153, 144)
LEFT_EYE = (362, 385, 387, 263, 373, 380)
RIGHT_IRIS = (469, 470, 471, 472)
LEFT_IRIS = (474, 475, 476, 477)


class MediaPipeFaceLandmarker:
    def __init__(self, model_path: Path) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Face landmarker model not found at {model_path}; "
                "run `uv run python -m spare_my_eyes.model_asset`"
            )
        self._landmarker = FaceLandmarker.create_from_options(_options(model_path))
        self._last_timestamp_ms = -1

    def detect(self, frame: Frame, timestamp: float) -> FaceSample:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, self._next_timestamp_ms(timestamp))
        if not result.face_landmarks:
            return FaceSample.absent(timestamp)
        height, width = frame.shape[:2]
        points = [(float(mark.x) * width, float(mark.y) * height) for mark in result.face_landmarks[0]]
        return _sample_from(points, result.facial_transformation_matrixes[0], timestamp)

    def close(self) -> None:
        self._landmarker.close()

    def _next_timestamp_ms(self, timestamp: float) -> int:
        self._last_timestamp_ms = max(int(timestamp * 1000), self._last_timestamp_ms + 1)
        return self._last_timestamp_ms


def _options(model_path: Path) -> FaceLandmarkerOptions:
    return FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_buffer=model_path.read_bytes()),
        running_mode=RunningMode.VIDEO,
        num_faces=1,
        output_facial_transformation_matrixes=True,
    )


def _sample_from(points: Sequence[Point], matrix: object, timestamp: float) -> FaceSample:
    rotation = np.asarray(matrix, dtype=float)[:3, :3].tolist()
    left_iris = iris_diameter(_pick(points, LEFT_IRIS))
    right_iris = iris_diameter(_pick(points, RIGHT_IRIS))
    return FaceSample(
        timestamp=timestamp,
        face_present=True,
        left_ear=eye_aspect_ratio(_pick(points, LEFT_EYE)),
        right_ear=eye_aspect_ratio(_pick(points, RIGHT_EYE)),
        iris_diameter_px=(left_iris + right_iris) / 2,
        head_yaw_degrees=yaw_degrees(rotation),
    )


def _pick(points: Sequence[Point], indices: Sequence[int]) -> list[Point]:
    return [points[index] for index in indices]
```

- [ ] **Step 9: Run and pin the yaw sign**

Run: `uv run pytest tests/integration/test_mediapipe_landmarker.py -v`
Expected: all pass, or the yaw tests are skipped if a fixture is missing.

If `test_detect_head_turned_left_reports_negative_yaw` fails with a *positive* value of similar size, and the mirrored test fails with a *negative* one, then MediaPipe's axis is mirrored relative to the project's convention (negative = user's left). Fix it in `_sample_from` by passing `head_yaw_degrees=-yaw_degrees(rotation)`, then re-run. Any other failure (no face, EAR out of range) means the fixture image is unsuitable: replace the image, not the thresholds.

- [ ] **Step 10: Run all checks**

Run: `uv run pytest && uv run mypy && uv run ruff check .`
Expected: all passed (fixture-dependent tests may be skipped with the CREDITS message), mypy and ruff clean.

- [ ] **Step 11: Commit**

```bash
git add src/spare_my_eyes/model_asset.py src/spare_my_eyes/assets/.gitkeep src/spare_my_eyes/capture/landmarker.py src/spare_my_eyes/capture/mediapipe_landmarker.py tests/unit/test_model_asset.py tests/integration/face_images.py tests/integration/test_mediapipe_landmarker.py tests/fixtures
git commit -m "feat: extract EAR, iris size and yaw with MediaPipe Face Landmarker

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 20: CameraFaceSampleSource, build_sample_source and CaptureWorker

**Files:**
- Create: `src/spare_my_eyes/capture/camera_sample_source.py`, `src/spare_my_eyes/capture/source_factory.py`, `src/spare_my_eyes/capture/worker.py`
- Create: `tests/fakes/sample_sources.py`, `tests/fakes/waiting.py`
- Test: `tests/unit/test_capture_worker.py`, `tests/unit/test_source_factory.py`, `tests/integration/test_camera_sample_source.py`

**Interfaces:**
- Consumes: `FrameSource`, `OpenCvFrameSource` (Task 18), `FaceLandmarkDetector`, `MediaPipeFaceLandmarker`, `MODEL_PATH` (Task 19), `FaceSampleSource`, `CameraStatus`, `UnavailableSampleSource`, `ScriptedFaceSampleSource`, `SCENARIOS` (Task 12), `Settings`, `Clock`, `log_event`.
- Produces:
  - `CameraFaceSampleSource(frames: FrameSource, detector: FaceLandmarkDetector, clock: Clock)`: a `FaceSampleSource`. The frame is a local variable and is dropped once the sample exists.
  - `build_sample_source(scripted_camera: str | None, settings: Settings, clock: Clock, logger: logging.Logger, model_path: Path = MODEL_PATH) -> FaceSampleSource`. A missing model logs `model_missing` and returns `UnavailableSampleSource`.
  - `CameraStatusChanged(status: CameraStatus)`, frozen; `CaptureMessage = FaceSample | CameraStatusChanged`.
  - `CaptureWorker(source: FaceSampleSource, outbox: queue.Queue[CaptureMessage], retry_seconds: float, logger: logging.Logger, restart_delay_seconds: float = 1.0)` with `start()`, `stop(timeout_seconds=5.0)`, `suspend()`, `resume()`, properties `is_suspended`, `is_running`. Logs `camera_failed` (status, reason) and `capture_thread_crashed` (with traceback).
  - Fakes: `FailingSampleSource(error)`, `CrashOnceSampleSource()`, `SteadySampleSource()` (each counts `open_calls`, `close_calls`); `wait_until(condition, timeout_seconds=2.0) -> bool`.

- [ ] **Step 1: Write the fakes**

`tests/fakes/waiting.py`:

```python
import time
from collections.abc import Callable

POLL_SECONDS = 0.01


def wait_until(condition: Callable[[], bool], timeout_seconds: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(POLL_SECONDS)
    return condition()
```

`tests/fakes/sample_sources.py`:

```python
import time

from spare_my_eyes.capture.face_sample import FaceSample

SAMPLE_PACE_SECONDS = 0.005


class FailingSampleSource:
    def __init__(self, error: Exception) -> None:
        self._error = error
        self.open_calls = 0
        self.close_calls = 0

    def open(self) -> None:
        self.open_calls += 1
        raise self._error

    def next_sample(self) -> FaceSample:
        raise self._error

    def close(self) -> None:
        self.close_calls += 1


class SteadySampleSource:
    def __init__(self) -> None:
        self.open_calls = 0
        self.close_calls = 0

    def open(self) -> None:
        self.open_calls += 1

    def next_sample(self) -> FaceSample:
        time.sleep(SAMPLE_PACE_SECONDS)
        return FaceSample(timestamp=time.monotonic(), face_present=True)

    def close(self) -> None:
        self.close_calls += 1


class CrashOnceSampleSource(SteadySampleSource):
    def open(self) -> None:
        super().open()
        if self.open_calls == 1:
            raise RuntimeError("simulated crash on first open")
```

- [ ] **Step 2: Write the failing tests**

`tests/unit/test_capture_worker.py`:

```python
import queue

import pytest

from spare_my_eyes.capture.camera_errors import CameraBusyError, CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus, FaceSampleSource
from spare_my_eyes.capture.worker import CameraStatusChanged, CaptureMessage, CaptureWorker
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.sample_sources import (
    CrashOnceSampleSource,
    FailingSampleSource,
    SteadySampleSource,
)
from tests.fakes.waiting import wait_until

RETRY_SECONDS = 0.05


@pytest.fixture
def outbox() -> queue.Queue[CaptureMessage]:
    return queue.Queue()


def make_worker(
    source: FaceSampleSource, outbox: queue.Queue[CaptureMessage], log: RecordingLogHandler
) -> CaptureWorker:
    return CaptureWorker(source, outbox, RETRY_SECONDS, log.logger, restart_delay_seconds=0.01)


def test_start_working_camera_reports_active_then_samples(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    worker = make_worker(SteadySampleSource(), outbox, log_recorder)
    worker.start()
    try:
        first, second = outbox.get(timeout=2), outbox.get(timeout=2)
    finally:
        worker.stop()
    assert first == CameraStatusChanged(CameraStatus.ACTIVE)
    assert isinstance(second, FaceSample)


def test_start_missing_camera_reports_unavailable_and_retries(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    source = FailingSampleSource(CameraUnavailableError("no camera at index 0"))
    worker = make_worker(source, outbox, log_recorder)
    worker.start()
    try:
        assert wait_until(lambda: source.open_calls >= 2)
    finally:
        worker.stop()
    assert outbox.get(timeout=1) == CameraStatusChanged(CameraStatus.UNAVAILABLE)
    assert log_recorder.fields_of("camera_failed")["status"] == "unavailable"


def test_start_busy_camera_reports_busy(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    worker = make_worker(FailingSampleSource(CameraBusyError("in use")), outbox, log_recorder)
    worker.start()
    try:
        message = outbox.get(timeout=2)
    finally:
        worker.stop()
    assert message == CameraStatusChanged(CameraStatus.BUSY)


def test_start_unexpected_error_logs_and_restarts(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    worker = make_worker(CrashOnceSampleSource(), outbox, log_recorder)
    worker.start()
    try:
        message = outbox.get(timeout=2)
    finally:
        worker.stop()
    assert message == CameraStatusChanged(CameraStatus.ACTIVE)
    assert "capture_thread_crashed" in log_recorder.events()


def test_suspend_releases_camera_and_resume_reopens_it(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    source = SteadySampleSource()
    worker = make_worker(source, outbox, log_recorder)
    worker.start()
    try:
        assert wait_until(lambda: source.open_calls == 1)
        worker.suspend()
        assert wait_until(lambda: source.close_calls >= 1)
        worker.resume()
        assert wait_until(lambda: source.open_calls == 2)
    finally:
        worker.stop()


def test_stop_running_worker_ends_thread(
    outbox: queue.Queue[CaptureMessage], log_recorder: RecordingLogHandler
) -> None:
    worker = make_worker(SteadySampleSource(), outbox, log_recorder)
    worker.start()
    worker.stop()
    assert not worker.is_running
```

`tests/unit/test_source_factory.py`:

```python
from pathlib import Path

from spare_my_eyes.capture.sample_source import UnavailableSampleSource
from spare_my_eyes.capture.scripted import ScriptedFaceSampleSource
from spare_my_eyes.capture.source_factory import build_sample_source
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.logs import RecordingLogHandler


def test_build_sample_source_scripted_name_returns_scripted_source(
    log_recorder: RecordingLogHandler,
) -> None:
    source = build_sample_source("normal", Settings(), FakeClock(), log_recorder.logger)
    assert isinstance(source, ScriptedFaceSampleSource)


def test_build_sample_source_missing_model_returns_unavailable_source(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    missing = tmp_path / "face_landmarker.task"
    source = build_sample_source(None, Settings(), FakeClock(), log_recorder.logger, missing)
    assert isinstance(source, UnavailableSampleSource)
    assert log_recorder.fields_of("model_missing") == {"path": str(missing)}
```

`tests/integration/test_camera_sample_source.py`:

```python
import pytest

from spare_my_eyes.capture.camera_errors import CameraBusyError
from spare_my_eyes.capture.camera_sample_source import CameraFaceSampleSource
from spare_my_eyes.capture.mediapipe_landmarker import MediaPipeFaceLandmarker
from spare_my_eyes.capture.source_factory import build_sample_source
from spare_my_eyes.model_asset import MODEL_PATH
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.frame_sources import FailingFrameSource, StillImageFrameSource
from tests.fakes.logs import RecordingLogHandler
from tests.integration.face_images import blank_frame, load_face

pytestmark = pytest.mark.mediapipe


def test_next_sample_still_face_image_reports_face_with_clock_time() -> None:
    frames = StillImageFrameSource(load_face("frontal_eyes_open.jpg"))
    source = CameraFaceSampleSource(frames, MediaPipeFaceLandmarker(MODEL_PATH), FakeClock(42.0))
    source.open()
    sample = source.next_sample()
    assert sample.face_present
    assert sample.timestamp == 42.0


def test_next_sample_blank_frame_reports_no_face() -> None:
    frames = StillImageFrameSource(blank_frame())
    source = CameraFaceSampleSource(frames, MediaPipeFaceLandmarker(MODEL_PATH), FakeClock())
    source.open()
    assert not source.next_sample().face_present


def test_next_sample_busy_camera_raises_camera_busy() -> None:
    frames = FailingFrameSource(read_error=CameraBusyError("in use by another app"))
    source = CameraFaceSampleSource(frames, MediaPipeFaceLandmarker(MODEL_PATH), FakeClock())
    source.open()
    with pytest.raises(CameraBusyError):
        source.next_sample()


def test_build_sample_source_with_model_returns_camera_source(
    log_recorder: RecordingLogHandler,
) -> None:
    source = build_sample_source(None, Settings(), FakeClock(), log_recorder.logger)
    assert isinstance(source, CameraFaceSampleSource)
```

- [ ] **Step 3: Run to see them fail**

Run: `uv run pytest tests/unit/test_capture_worker.py tests/unit/test_source_factory.py tests/integration/test_camera_sample_source.py -v`
Expected: FAIL with `ModuleNotFoundError` for `spare_my_eyes.capture.worker`, `...source_factory`, `...camera_sample_source`.

- [ ] **Step 4: Implement the camera sample source**

`src/spare_my_eyes/capture/camera_sample_source.py`:

```python
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.frame_source import FrameSource
from spare_my_eyes.capture.landmarker import FaceLandmarkDetector
from spare_my_eyes.clock import Clock


class CameraFaceSampleSource:
    def __init__(self, frames: FrameSource, detector: FaceLandmarkDetector, clock: Clock) -> None:
        self._frames = frames
        self._detector = detector
        self._clock = clock

    def open(self) -> None:
        self._frames.open()

    def next_sample(self) -> FaceSample:
        frame = self._frames.read()
        return self._detector.detect(frame, self._clock.now())

    def close(self) -> None:
        self._frames.close()
```

- [ ] **Step 5: Implement the source factory**

`src/spare_my_eyes/capture/source_factory.py`:

```python
import logging
from pathlib import Path

from spare_my_eyes.capture.camera_sample_source import CameraFaceSampleSource
from spare_my_eyes.capture.mediapipe_landmarker import MediaPipeFaceLandmarker
from spare_my_eyes.capture.opencv_frame_source import OpenCvFrameSource
from spare_my_eyes.capture.sample_source import FaceSampleSource, UnavailableSampleSource
from spare_my_eyes.capture.scenarios import SCENARIOS
from spare_my_eyes.capture.scripted import ScriptedFaceSampleSource
from spare_my_eyes.clock import Clock
from spare_my_eyes.model_asset import MODEL_PATH
from spare_my_eyes.settings import Settings
from spare_my_eyes.structured_log import log_event


def build_sample_source(
    scripted_camera: str | None,
    settings: Settings,
    clock: Clock,
    logger: logging.Logger,
    model_path: Path = MODEL_PATH,
) -> FaceSampleSource:
    if scripted_camera is not None:
        return _scripted_source(scripted_camera, settings, clock)
    if not model_path.is_file():
        log_event(logger, logging.ERROR, "model_missing", path=str(model_path))
        return UnavailableSampleSource(
            f"Face landmarker model missing at {model_path}; "
            "run `uv run python -m spare_my_eyes.model_asset`"
        )
    frames = OpenCvFrameSource(settings.camera_index, fps=settings.frames_per_second)
    return CameraFaceSampleSource(frames, MediaPipeFaceLandmarker(model_path), clock)


def _scripted_source(name: str, settings: Settings, clock: Clock) -> ScriptedFaceSampleSource:
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scripted camera {name!r}; expected one of {sorted(SCENARIOS)}")
    return ScriptedFaceSampleSource(SCENARIOS[name], settings.frames_per_second, clock)
```

- [ ] **Step 6: Implement the worker**

`src/spare_my_eyes/capture/worker.py`:

```python
import logging
import queue
import threading
from dataclasses import dataclass

from spare_my_eyes.capture.camera_errors import CameraBusyError, CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import CameraStatus, FaceSampleSource
from spare_my_eyes.structured_log import log_event


@dataclass(frozen=True, slots=True)
class CameraStatusChanged:
    status: CameraStatus


CaptureMessage = FaceSample | CameraStatusChanged


class CaptureWorker:
    """Reads face samples on a background thread and posts them to the main thread's queue."""

    SUSPENDED_POLL_SECONDS = 0.5

    def __init__(
        self,
        source: FaceSampleSource,
        outbox: queue.Queue[CaptureMessage],
        retry_seconds: float,
        logger: logging.Logger,
        restart_delay_seconds: float = 1.0,
    ) -> None:
        self._source = source
        self._outbox = outbox
        self._retry_seconds = retry_seconds
        self._logger = logger
        self._restart_delay = restart_delay_seconds
        self._stopping = threading.Event()
        self._suspended = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_suspended(self) -> bool:
        return self._suspended.is_set()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="capture", daemon=True)
        self._thread.start()

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(timeout_seconds)

    def suspend(self) -> None:
        self._suspended.set()

    def resume(self) -> None:
        self._suspended.clear()

    def _run(self) -> None:
        while not self._stopping.is_set():
            if self._suspended.is_set():
                self._stopping.wait(self.SUSPENDED_POLL_SECONDS)
                continue
            self._run_capture_session()

    def _run_capture_session(self) -> None:
        try:
            self._capture_until_interrupted()
        except CameraUnavailableError as error:
            self._wait_after_failure(CameraStatus.UNAVAILABLE, error)
        except CameraBusyError as error:
            self._wait_after_failure(CameraStatus.BUSY, error)
        except Exception:
            self._logger.exception("capture_thread_crashed")
            self._stopping.wait(self._restart_delay)
        finally:
            self._source.close()

    def _capture_until_interrupted(self) -> None:
        self._source.open()
        self._outbox.put(CameraStatusChanged(CameraStatus.ACTIVE))
        while not self._stopping.is_set() and not self._suspended.is_set():
            self._outbox.put(self._source.next_sample())

    def _wait_after_failure(self, status: CameraStatus, error: Exception) -> None:
        log_event(
            self._logger, logging.WARNING, "camera_failed", status=status.value, reason=str(error)
        )
        self._outbox.put(CameraStatusChanged(status))
        self._stopping.wait(self._retry_seconds)
```

- [ ] **Step 7: Run to see them pass**

Run: `uv run pytest tests/unit/test_capture_worker.py tests/unit/test_source_factory.py tests/integration/test_camera_sample_source.py -v && uv run mypy`
Expected: all passed (the still-image test may be skipped if its fixture is missing), mypy clean.

- [ ] **Step 8: Commit**

```bash
git add src/spare_my_eyes/capture/camera_sample_source.py src/spare_my_eyes/capture/source_factory.py src/spare_my_eyes/capture/worker.py tests/fakes/sample_sources.py tests/fakes/waiting.py tests/unit/test_capture_worker.py tests/unit/test_source_factory.py tests/integration/test_camera_sample_source.py
git commit -m "feat: capture face samples on a resilient background worker

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 21: UI — notification text, overlays, cards, tray and TkNotifier

**Files:**
- Create: `src/spare_my_eyes/ui/__init__.py`, `src/spare_my_eyes/ui/notification_text.py`, `src/spare_my_eyes/ui/theme.py`, `src/spare_my_eyes/ui/window_style.py`, `src/spare_my_eyes/ui/message_overlay.py`, `src/spare_my_eyes/ui/card_window.py`, `src/spare_my_eyes/ui/break_card.py`, `src/spare_my_eyes/ui/tray_icon.py`, `src/spare_my_eyes/ui/tk_notifier.py`
- Create: `tests/fakes/tray.py`
- Test: `tests/unit/test_notification_text.py`, `tests/integration/test_tk_notifier.py`, `tests/integration/test_tray_icon.py`

**Interfaces:**
- Consumes: `BreakProgress`, `BreakStep` (Task 11), `CalibrationProgress`, `CalibrationStep`, `CalibrationSession.STEP_SECONDS` (Task 9), `Notifier`, `TrayStatus` (Task 13), `log_event`.
- Produces:
  - `CardText(title: str, detail: str, fraction_done: float)`; `describe_break(progress) -> CardText`; `describe_calibration(progress) -> CardText`; `describe_status(status, blinks_per_minute) -> str`; `snooze_label(snooze_seconds: float) -> str`; `SKIP_LABEL = "Skip"`.
  - `window_style`: `prepare_hidden_tool_window(window, alpha)`, `show_without_focus(window)`, `hide_window(window)`, `is_window_visible(window) -> bool`, `is_foreground(window) -> bool`.
  - `MessageOverlay(root: tk.Tk, stack_index: int)` with `show(message)`, `hide()`, properties `is_visible`, `text`, `window`.
  - `CardWindow(root: tk.Tk)` with `show(text: CardText)`, `hide()`, properties `is_visible`, `title`, `detail`, `window`.
  - `BreakCard(root, snooze_text: str, on_snooze: Callable[[], None], on_skip: Callable[[], None])` with `.card: CardWindow`, `.snooze_button`, `.skip_button`.
  - `TrayMenuActions(pause_for_hour, start_break, recalibrate, open_settings, quit)` (each `Callable[[], None]`); `TrayIcon(actions)` with `start()`, `stop()`, `set_status(status, blinks_per_minute)`, `menu_labels() -> list[str]`, property `title`; `status_icon_image(status) -> Image.Image`.
  - `TrayStatusView` protocol: `set_status(status, blinks_per_minute)`.
  - `TkNotifier(nudge: MessageOverlay, distance: MessageOverlay, break_card: CardWindow, calibration_card: CardWindow, tray: TrayStatusView, logger: logging.Logger)` implementing `Notifier`; logs `notification_shown` (kind) each time a hidden window becomes visible.
  - Fake `FakeTray` with `statuses: list[tuple[TrayStatus, float | None]]`, `started`, `stopped`.

Windows are shown with `ShowWindow(SW_SHOWNOACTIVATE)` and carry `WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW`, so they never take focus and stay out of Alt+Tab. Tk's own `withdraw`/`deiconify` are not used after setup.

- [ ] **Step 1: Write the failing pure-text tests**

`tests/unit/test_notification_text.py`:

```python
import pytest

from spare_my_eyes.calibration import CalibrationProgress, CalibrationStep
from spare_my_eyes.coaching.break_session import BreakProgress, BreakStep
from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.ui.notification_text import (
    describe_break,
    describe_calibration,
    describe_status,
    snooze_label,
)


def progress(step: BreakStep, gaze: float, blinks: int, verified: bool = True) -> BreakProgress:
    return BreakProgress(step, gaze, 20.0, blinks, 5, verified)


def test_describe_break_look_out_step_shows_gaze_seconds() -> None:
    text = describe_break(progress(BreakStep.LOOK_OUT, 7.4, 0))
    assert text.title == "Look out the window"
    assert text.detail == "7 / 20 s"
    assert text.fraction_done == pytest.approx(0.185)


def test_describe_break_slow_blink_step_shows_blink_count() -> None:
    text = describe_break(progress(BreakStep.SLOW_BLINKS, 20.0, 2))
    assert text.title == "5 slow, complete blinks"
    assert text.detail == "2 / 5"
    assert text.fraction_done == pytest.approx(0.7)


def test_describe_break_unverified_mentions_honor_system() -> None:
    text = describe_break(progress(BreakStep.LOOK_OUT, 0.0, 0, verified=False))
    assert "honor system" in text.detail


def test_describe_calibration_arm_length_step_shows_instruction_and_time() -> None:
    text = describe_calibration(CalibrationProgress(CalibrationStep.ARM_LENGTH, 4.2))
    assert "arm's length" in text.title
    assert text.detail == "4 s left"
    assert text.fraction_done == pytest.approx(0.58)


def test_describe_status_monitoring_with_rate_includes_rate() -> None:
    assert describe_status(TrayStatus.MONITORING, 11.6) == "Spare My Eyes: monitoring, 12 blinks/min"


def test_describe_status_no_camera_omits_rate() -> None:
    assert describe_status(TrayStatus.NO_CAMERA, 11.6) == "Spare My Eyes: no camera"


def test_snooze_label_default_snooze_reads_five_minutes() -> None:
    assert snooze_label(300.0) == "Snooze 5 min"
```

- [ ] **Step 2: Run to see them fail**

Run: `uv run pytest tests/unit/test_notification_text.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.ui'`.

- [ ] **Step 3: Implement the text module**

`src/spare_my_eyes/ui/__init__.py`: empty.

`src/spare_my_eyes/ui/notification_text.py`:

```python
from dataclasses import dataclass

from spare_my_eyes.calibration import CalibrationProgress, CalibrationSession, CalibrationStep
from spare_my_eyes.coaching.break_session import BreakProgress, BreakStep
from spare_my_eyes.coaching.notifier import TrayStatus

LOOK_OUT_TITLE = "Look out the window"
HONOR_SYSTEM_NOTE = "camera off, honor system"
SKIP_LABEL = "Skip"

_CALIBRATION_TITLES = {
    CalibrationStep.LOOK_AT_SCREEN: "Look at the screen as you normally do",
    CalibrationStep.ARM_LENGTH: "Sit at arm's length from the screen (about 60 cm)",
    CalibrationStep.DONE: "Calibration done",
}

_STATUS_LABELS = {
    TrayStatus.MONITORING: "monitoring",
    TrayStatus.PAUSED: "paused",
    TrayStatus.NO_CAMERA: "no camera",
    TrayStatus.CALIBRATING: "calibrating",
}


@dataclass(frozen=True, slots=True)
class CardText:
    title: str
    detail: str
    fraction_done: float


def describe_break(progress: BreakProgress) -> CardText:
    fraction = _break_fraction(progress)
    if progress.step is BreakStep.LOOK_OUT:
        detail = f"{progress.gaze_seconds:.0f} / {progress.gaze_target_seconds:.0f} s"
        return CardText(LOOK_OUT_TITLE, _with_note(detail, progress), fraction)
    title = f"{progress.slow_blink_target} slow, complete blinks"
    detail = f"{progress.slow_blinks} / {progress.slow_blink_target}"
    return CardText(title, _with_note(detail, progress), fraction)


def describe_calibration(progress: CalibrationProgress) -> CardText:
    fraction = 1.0 - progress.seconds_left / CalibrationSession.STEP_SECONDS
    detail = f"{progress.seconds_left:.0f} s left"
    return CardText(_CALIBRATION_TITLES[progress.step], detail, fraction)


def describe_status(status: TrayStatus, blinks_per_minute: float | None) -> str:
    label = f"Spare My Eyes: {_STATUS_LABELS[status]}"
    if blinks_per_minute is None or status is not TrayStatus.MONITORING:
        return label
    return f"{label}, {blinks_per_minute:.0f} blinks/min"


def snooze_label(snooze_seconds: float) -> str:
    return f"Snooze {snooze_seconds / 60:.0f} min"


def _break_fraction(progress: BreakProgress) -> float:
    gaze = min(progress.gaze_seconds / progress.gaze_target_seconds, 1.0)
    blinks = min(progress.slow_blinks / progress.slow_blink_target, 1.0)
    return 0.5 * gaze + 0.5 * blinks


def _with_note(detail: str, progress: BreakProgress) -> str:
    return detail if progress.verified else f"{detail} ({HONOR_SYSTEM_NOTE})"
```

Run: `uv run pytest tests/unit/test_notification_text.py -v`
Expected: 7 passed.

- [ ] **Step 4: Write the fake tray and the failing GUI tests**

`tests/fakes/tray.py`:

```python
from spare_my_eyes.coaching.notifier import TrayStatus


class FakeTray:
    def __init__(self) -> None:
        self.statuses: list[tuple[TrayStatus, float | None]] = []
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None:
        self.statuses.append((status, blinks_per_minute))
```

`tests/integration/test_tk_notifier.py`:

```python
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
def rig(log_recorder: RecordingLogHandler) -> Iterator[UiRig]:
    root = tk.Tk()
    root.withdraw()
    presses: list[str] = []
    nudge, distance = MessageOverlay(root, 0), MessageOverlay(root, 1)
    card = BreakCard(root, "Snooze 5 min", lambda: presses.append("snooze"), lambda: presses.append("skip"))
    calibration, tray = CardWindow(root), FakeTray()
    notifier = TkNotifier(nudge, distance, card.card, calibration, tray, log_recorder.logger)
    yield UiRig(notifier, nudge, distance, card, calibration, tray, presses)
    root.destroy()


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
```

`tests/integration/test_tray_icon.py`:

```python
import pytest

from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.ui.tray_icon import TrayIcon, TrayMenuActions, status_icon_image

pytestmark = pytest.mark.gui


def do_nothing() -> None:
    return None


ACTIONS = TrayMenuActions(do_nothing, do_nothing, do_nothing, do_nothing, do_nothing)


def test_menu_labels_match_spec() -> None:
    assert TrayIcon(ACTIONS).menu_labels() == [
        "Pause for 1 hour",
        "Start break now",
        "Recalibrate",
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
```

- [ ] **Step 5: Run to see them fail**

Run: `uv run pytest tests/integration/test_tk_notifier.py tests/integration/test_tray_icon.py -v`
Expected: FAIL with `ModuleNotFoundError` for `spare_my_eyes.ui.break_card` (and the other UI modules).

- [ ] **Step 6: Implement theme and window style**

`src/spare_my_eyes/ui/theme.py`:

```python
BACKGROUND = "#263238"
FOREGROUND = "#ffffff"
MUTED = "#b0bec5"
OVERLAY_FONT = ("Segoe UI", 14)
TITLE_FONT = ("Segoe UI Semibold", 15)
DETAIL_FONT = ("Segoe UI", 11)
```

`src/spare_my_eyes/ui/window_style.py`:

```python
import ctypes
import tkinter as tk

_GWL_EXSTYLE = -20
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_NOACTIVATE = 0x08000000
_SW_HIDE = 0
_SW_SHOWNOACTIVATE = 4


def native_handle(window: tk.Toplevel) -> int:
    return int(ctypes.windll.user32.GetParent(window.winfo_id()))


def prepare_hidden_tool_window(window: tk.Toplevel, alpha: float) -> None:
    window.attributes("-alpha", 0.0)
    window.update_idletasks()
    user32 = ctypes.windll.user32
    handle = native_handle(window)
    style = int(user32.GetWindowLongW(handle, _GWL_EXSTYLE))
    user32.SetWindowLongW(handle, _GWL_EXSTYLE, style | _WS_EX_TOOLWINDOW | _WS_EX_NOACTIVATE)
    hide_window(window)
    window.attributes("-alpha", alpha)


def show_without_focus(window: tk.Toplevel) -> None:
    ctypes.windll.user32.ShowWindow(native_handle(window), _SW_SHOWNOACTIVATE)


def hide_window(window: tk.Toplevel) -> None:
    ctypes.windll.user32.ShowWindow(native_handle(window), _SW_HIDE)


def is_window_visible(window: tk.Toplevel) -> bool:
    return bool(ctypes.windll.user32.IsWindowVisible(native_handle(window)))


def is_foreground(window: tk.Toplevel) -> bool:
    return int(ctypes.windll.user32.GetForegroundWindow()) == native_handle(window)
```

- [ ] **Step 7: Implement the overlay and the cards**

`src/spare_my_eyes/ui/message_overlay.py`:

```python
import tkinter as tk

from spare_my_eyes.ui.theme import BACKGROUND, FOREGROUND, OVERLAY_FONT
from spare_my_eyes.ui.window_style import (
    hide_window,
    is_window_visible,
    prepare_hidden_tool_window,
    show_without_focus,
)


class MessageOverlay:
    """Small semi-transparent corner notice that never takes focus."""

    WIDTH = 280
    HEIGHT = 56
    MARGIN = 24
    TASKBAR_ALLOWANCE = 48
    ALPHA = 0.85

    def __init__(self, root: tk.Tk, stack_index: int) -> None:
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(background=BACKGROUND)
        self._label = tk.Label(self.window, font=OVERLAY_FONT, fg=FOREGROUND, bg=BACKGROUND)
        self._label.pack(expand=True, fill="both")
        self.window.geometry(self._geometry(root, stack_index))
        prepare_hidden_tool_window(self.window, self.ALPHA)

    @property
    def is_visible(self) -> bool:
        return is_window_visible(self.window)

    @property
    def text(self) -> str:
        return str(self._label.cget("text"))

    def show(self, message: str) -> None:
        self._label.configure(text=message)
        if not self.is_visible:
            show_without_focus(self.window)

    def hide(self) -> None:
        hide_window(self.window)

    def _geometry(self, root: tk.Tk, stack_index: int) -> str:
        x = root.winfo_screenwidth() - self.WIDTH - self.MARGIN
        rows_from_bottom = (self.HEIGHT + self.MARGIN) * (stack_index + 1)
        y = root.winfo_screenheight() - rows_from_bottom - self.TASKBAR_ALLOWANCE
        return f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}"
```

`src/spare_my_eyes/ui/card_window.py`:

```python
import tkinter as tk
from tkinter import ttk

from spare_my_eyes.ui.notification_text import CardText
from spare_my_eyes.ui.theme import BACKGROUND, DETAIL_FONT, FOREGROUND, MUTED, TITLE_FONT
from spare_my_eyes.ui.window_style import (
    hide_window,
    is_window_visible,
    prepare_hidden_tool_window,
    show_without_focus,
)


class CardWindow:
    """Borderless always-on-top card near the screen center that never takes focus."""

    WIDTH = 380
    HEIGHT = 170
    ALPHA = 0.95

    def __init__(self, root: tk.Tk) -> None:
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(background=BACKGROUND, padx=20, pady=16)
        self._title = _packed_label(self.window, TITLE_FONT, FOREGROUND)
        self._detail = _packed_label(self.window, DETAIL_FONT, MUTED)
        self._progress = ttk.Progressbar(self.window, maximum=1.0, length=self.WIDTH - 40)
        self._progress.pack(fill="x", pady=(8, 10))
        self.window.geometry(_centered(root, self.WIDTH, self.HEIGHT))
        prepare_hidden_tool_window(self.window, self.ALPHA)

    @property
    def is_visible(self) -> bool:
        return is_window_visible(self.window)

    @property
    def title(self) -> str:
        return str(self._title.cget("text"))

    @property
    def detail(self) -> str:
        return str(self._detail.cget("text"))

    def show(self, text: CardText) -> None:
        self._title.configure(text=text.title)
        self._detail.configure(text=text.detail)
        self._progress.configure(value=text.fraction_done)
        if not self.is_visible:
            show_without_focus(self.window)

    def hide(self) -> None:
        hide_window(self.window)


def _packed_label(parent: tk.Toplevel, font: tuple[str, int], color: str) -> tk.Label:
    label = tk.Label(parent, font=font, fg=color, bg=BACKGROUND, anchor="w", justify="left")
    label.pack(fill="x")
    return label


def _centered(root: tk.Tk, width: int, height: int) -> str:
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 3
    return f"{width}x{height}+{x}+{y}"
```

`src/spare_my_eyes/ui/break_card.py`:

```python
import tkinter as tk
from collections.abc import Callable

from spare_my_eyes.ui.card_window import CardWindow
from spare_my_eyes.ui.notification_text import SKIP_LABEL
from spare_my_eyes.ui.theme import BACKGROUND


class BreakCard:
    def __init__(
        self,
        root: tk.Tk,
        snooze_text: str,
        on_snooze: Callable[[], None],
        on_skip: Callable[[], None],
    ) -> None:
        self.card = CardWindow(root)
        buttons = tk.Frame(self.card.window, background=BACKGROUND)
        buttons.pack(fill="x")
        self.snooze_button = tk.Button(buttons, text=snooze_text, command=on_snooze)
        self.snooze_button.pack(side="left")
        self.skip_button = tk.Button(buttons, text=SKIP_LABEL, command=on_skip)
        self.skip_button.pack(side="right")
```

- [ ] **Step 8: Implement the tray icon**

`src/spare_my_eyes/ui/tray_icon.py`:

```python
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

    @property
    def title(self) -> str:
        return str(self._icon.title)

    def menu_labels(self) -> list[str]:
        return [str(item.text) for item in self._icon.menu.items]

    def start(self) -> None:
        self._icon.run_detached()

    def stop(self) -> None:
        self._icon.stop()

    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None:
        self._icon.icon = status_icon_image(status)
        self._icon.title = describe_status(status, blinks_per_minute)


def _menu(actions: TrayMenuActions) -> pystray.Menu:
    return pystray.Menu(
        pystray.MenuItem("Pause for 1 hour", lambda: actions.pause_for_hour()),
        pystray.MenuItem("Start break now", lambda: actions.start_break()),
        pystray.MenuItem("Recalibrate", lambda: actions.recalibrate()),
        pystray.MenuItem("Settings", lambda: actions.open_settings()),
        pystray.MenuItem("Quit", lambda: actions.quit()),
    )
```

The zero-argument lambdas matter: pystray inspects the callable's argument count, which a dataclass field holding a `functools.partial` would break.

- [ ] **Step 9: Implement TkNotifier**

`src/spare_my_eyes/ui/tk_notifier.py`:

```python
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
```

- [ ] **Step 10: Run to see them pass**

Run: `uv run pytest tests/unit/test_notification_text.py tests/integration/test_tk_notifier.py tests/integration/test_tray_icon.py -v && uv run mypy`
Expected: all passed, mypy clean. If mypy flags `ctypes.windll` or a Tk font tuple type, fix the annotation; do not add `# type: ignore` without a reason in the commit message.

- [ ] **Step 11: Commit**

```bash
git add src/spare_my_eyes/ui tests/fakes/tray.py tests/unit/test_notification_text.py tests/integration/test_tk_notifier.py tests/integration/test_tray_icon.py
git commit -m "feat: add focus-safe overlays, break and calibration cards, and tray icon

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 22: Settings window, start-with-Windows and live settings

**Files:**
- Create: `src/spare_my_eyes/settings_form.py`, `src/spare_my_eyes/settings_editor.py`, `src/spare_my_eyes/system/startup_registration.py`, `src/spare_my_eyes/ui/settings_window.py`
- Modify: `src/spare_my_eyes/coaching/controller.py` (add `apply_settings`, remember camera status)
- Modify: `src/spare_my_eyes/settings_store.py` (add `ensure_file`)
- Create: `tests/fakes/startup.py`, `tests/fakes/settings_editor.py`
- Test: `tests/unit/test_settings_form.py`, `tests/unit/test_settings_editor.py`, `tests/unit/test_controller.py` (append), `tests/unit/test_settings_store.py` (append), `tests/integration/test_startup_registration.py`, `tests/integration/test_settings_window.py`

**Interfaces:**
- Consumes: `Settings`, `WindowSide`, `JsonSettingsStore` (Task 8), `EyeCareController` (Task 17), `CameraStatus`.
- Produces:
  - `FieldRange(label, minimum, maximum)`; `BREAK_INTERVAL_MINUTES` (5–120), `BLINK_THRESHOLD` (3–20), `TOO_CLOSE_CM` (30–80), `CAMERA_INDEX` (0–9); `CLEAR_DISTANCE_MARGIN_CM = 5.0`.
  - `SettingsFormInput(window_side: str, break_interval_minutes: str, blink_threshold: str, too_close_cm: str, camera_index: str, start_with_windows: bool)` holds the raw widget text; `SettingsFormValues` holds the same fields parsed.
  - `form_input_from(settings, start_with_windows) -> SettingsFormInput`; `parse_form(form) -> SettingsFormValues` (raises `SettingsFormError` with `.problems: list[str]`, one message per bad field); `apply_form(settings, values) -> Settings`.
  - `StartupRegistration` protocol: property `is_available`, `is_enabled()`, `enable()`, `disable()`. `WindowsStartupRegistration(executable: Path | None, key_path=RUN_KEY_PATH, value_name="SpareMyEyes")` with extra `registered_command() -> str | None`; `installed_executable() -> Path | None` (only when running as the PyInstaller exe).
  - `EyeCareController.apply_settings(settings: Settings) -> None`: saves, rebuilds the Coach with the new values, re-sends the last camera status, logs `settings_applied`.
  - `JsonSettingsStore.ensure_file() -> Path`: creates `{}` if missing, never overwrites.
  - `SettingsEditor(controller: EyeCareController, startup: StartupRegistration)` with property `startup_available`, `current_form()`, `submit(form) -> list[str]` (empty list = saved).
  - `SettingsEditorPort` protocol (the three members above); `SettingsWindow(root, editor, open_file: Callable[[], None])` with public `tk` variables `window_side`, `break_interval`, `blink_threshold`, `too_close`, `camera_index`, `start_with_windows`, widgets `startup_checkbox`, `problems_label`, `open_file_button`, and methods `submit()`, `close()`, `bring_to_front()`, property `is_open`; `SettingsWindowOpener(root, editor, open_file)`, callable with no arguments, property `current`.
  - Fakes: `FakeStartupRegistration(available=True, enabled=False)`; `FakeSettingsEditor(form, problems=None, startup_available=True)` with `.submitted`.

Changing settings rebuilds the Coach, so the screen-time counter restarts. That is acceptable for a rare action and keeps the Coach immutable. The camera number applies after a restart, and the window says so.

- [ ] **Step 1: Write the fakes**

`tests/fakes/startup.py`:

```python
class FakeStartupRegistration:
    def __init__(self, available: bool = True, enabled: bool = False) -> None:
        self._available = available
        self.enabled = enabled

    @property
    def is_available(self) -> bool:
        return self._available

    def is_enabled(self) -> bool:
        return self.enabled

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False
```

`tests/fakes/settings_editor.py`:

```python
from spare_my_eyes.settings_form import SettingsFormInput


class FakeSettingsEditor:
    def __init__(
        self,
        form: SettingsFormInput,
        problems: list[str] | None = None,
        startup_available: bool = True,
    ) -> None:
        self.form = form
        self.problems = problems if problems is not None else []
        self.submitted: list[SettingsFormInput] = []
        self._startup_available = startup_available

    @property
    def startup_available(self) -> bool:
        return self._startup_available

    def current_form(self) -> SettingsFormInput:
        return self.form

    def submit(self, form: SettingsFormInput) -> list[str]:
        self.submitted.append(form)
        return self.problems
```

- [ ] **Step 2: Write the failing form tests**

`tests/unit/test_settings_form.py`:

```python
from dataclasses import replace

import pytest

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.settings import Settings
from spare_my_eyes.settings_form import (
    SettingsFormError,
    SettingsFormInput,
    apply_form,
    form_input_from,
    parse_form,
)

DEFAULT_FORM = SettingsFormInput("left", "20", "8", "50", "0", False)


def test_form_input_from_defaults_shows_spec_values() -> None:
    assert form_input_from(Settings(), start_with_windows=False) == DEFAULT_FORM


def test_parse_form_valid_input_returns_values() -> None:
    values = parse_form(replace(DEFAULT_FORM, window_side="right", break_interval_minutes=" 30 "))
    assert values.window_side is WindowSide.RIGHT
    assert values.break_interval_minutes == 30


def test_parse_form_several_bad_fields_reports_all_problems() -> None:
    form = replace(DEFAULT_FORM, break_interval_minutes="abc", too_close_cm="200")
    with pytest.raises(SettingsFormError) as caught:
        parse_form(form)
    assert len(caught.value.problems) == 2
    assert "Break every (minutes)" in caught.value.problems[0]
    assert "from 30 to 80, got '200'" in caught.value.problems[1]


def test_parse_form_unknown_window_side_reports_problem() -> None:
    with pytest.raises(SettingsFormError, match="Window side"):
        parse_form(replace(DEFAULT_FORM, window_side="up"))


def test_apply_form_converts_units_and_keeps_calibration() -> None:
    calibrated = replace(Settings(), open_ear_baseline=0.3, focal_scale=660.0)
    form = replace(DEFAULT_FORM, break_interval_minutes="30", too_close_cm="45", camera_index="1")
    settings = apply_form(calibrated, parse_form(form))
    assert settings.break_interval_seconds == 1800.0
    assert settings.too_close_cm == 45.0
    assert settings.distance_clear_cm == 50.0
    assert settings.camera_index == 1
    assert settings.open_ear_baseline == 0.3


def test_apply_form_unchanged_defaults_round_trip_to_defaults() -> None:
    assert apply_form(Settings(), parse_form(DEFAULT_FORM)) == Settings()
```

- [ ] **Step 3: Run to see them fail**

Run: `uv run pytest tests/unit/test_settings_form.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.settings_form'`.

- [ ] **Step 4: Implement the form model**

`src/spare_my_eyes/settings_form.py`:

```python
from dataclasses import dataclass, replace

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.settings import Settings

CLEAR_DISTANCE_MARGIN_CM = 5.0


@dataclass(frozen=True, slots=True)
class FieldRange:
    label: str
    minimum: int
    maximum: int


BREAK_INTERVAL_MINUTES = FieldRange("Break every (minutes)", 5, 120)
BLINK_THRESHOLD = FieldRange("Blink alert below (blinks/min)", 3, 20)
TOO_CLOSE_CM = FieldRange("Too close below (cm)", 30, 80)
CAMERA_INDEX = FieldRange("Camera number", 0, 9)


@dataclass(frozen=True, slots=True)
class SettingsFormInput:
    window_side: str
    break_interval_minutes: str
    blink_threshold: str
    too_close_cm: str
    camera_index: str
    start_with_windows: bool


@dataclass(frozen=True, slots=True)
class SettingsFormValues:
    window_side: WindowSide
    break_interval_minutes: int
    blink_threshold: int
    too_close_cm: int
    camera_index: int
    start_with_windows: bool


class SettingsFormError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def form_input_from(settings: Settings, start_with_windows: bool) -> SettingsFormInput:
    return SettingsFormInput(
        window_side=settings.window_side.value,
        break_interval_minutes=f"{settings.break_interval_seconds / 60:.0f}",
        blink_threshold=f"{settings.blink_rate_threshold_per_minute:.0f}",
        too_close_cm=f"{settings.too_close_cm:.0f}",
        camera_index=str(settings.camera_index),
        start_with_windows=start_with_windows,
    )


def parse_form(form: SettingsFormInput) -> SettingsFormValues:
    problems: list[str] = []
    values = SettingsFormValues(
        window_side=_window_side(form.window_side, problems),
        break_interval_minutes=_whole_number(
            form.break_interval_minutes, BREAK_INTERVAL_MINUTES, problems
        ),
        blink_threshold=_whole_number(form.blink_threshold, BLINK_THRESHOLD, problems),
        too_close_cm=_whole_number(form.too_close_cm, TOO_CLOSE_CM, problems),
        camera_index=_whole_number(form.camera_index, CAMERA_INDEX, problems),
        start_with_windows=form.start_with_windows,
    )
    if problems:
        raise SettingsFormError(problems)
    return values


def apply_form(settings: Settings, values: SettingsFormValues) -> Settings:
    return replace(
        settings,
        window_side=values.window_side,
        break_interval_seconds=values.break_interval_minutes * 60.0,
        blink_rate_threshold_per_minute=float(values.blink_threshold),
        too_close_cm=float(values.too_close_cm),
        distance_clear_cm=values.too_close_cm + CLEAR_DISTANCE_MARGIN_CM,
        camera_index=values.camera_index,
    )


def _whole_number(text: str, field: FieldRange, problems: list[str]) -> int:
    stripped = text.strip()
    if stripped.isdigit() and field.minimum <= int(stripped) <= field.maximum:
        return int(stripped)
    problems.append(
        f"{field.label} must be a whole number from {field.minimum} to {field.maximum}, "
        f"got {text!r}"
    )
    return field.minimum


def _window_side(text: str, problems: list[str]) -> WindowSide:
    if text in {side.value for side in WindowSide}:
        return WindowSide(text)
    problems.append(f"Window side must be 'left' or 'right', got {text!r}")
    return WindowSide.LEFT
```

Run: `uv run pytest tests/unit/test_settings_form.py -v`
Expected: 6 passed.

- [ ] **Step 5: Write the failing controller, store and editor tests**

Append to `tests/unit/test_controller.py`:

```python
def test_apply_settings_saves_and_rebuilds_coaching_with_new_values(
    log_recorder: RecordingLogHandler,
) -> None:
    rig = make_rig(CALIBRATED_SETTINGS, log_recorder)
    rig.controller.apply_settings(replace(CALIBRATED_SETTINGS, break_interval_seconds=2.0))
    assert rig.store.saved[-1].break_interval_seconds == 2.0
    rig.driver.play(TimelineSegment(4.0))
    assert rig.notifier.break_progress is not None
    assert "settings_applied" in log_recorder.events()


def test_apply_settings_keeps_known_camera_status(log_recorder: RecordingLogHandler) -> None:
    rig = make_rig(CALIBRATED_SETTINGS, log_recorder)
    rig.controller.on_camera_status(CameraStatus.UNAVAILABLE)
    rig.controller.apply_settings(CALIBRATED_SETTINGS)
    assert rig.notifier.status is TrayStatus.NO_CAMERA
```

Append to `tests/unit/test_settings_store.py`:

```python
def test_ensure_file_missing_creates_empty_overrides(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "SpareMyEyes" / "settings.json"
    assert JsonSettingsStore(path, log_recorder.logger).ensure_file() == path
    assert path.read_text(encoding="utf-8") == "{}\n"


def test_ensure_file_existing_file_is_left_untouched(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"window_side": "right"}', encoding="utf-8")
    JsonSettingsStore(path, log_recorder.logger).ensure_file()
    assert path.read_text(encoding="utf-8") == '{"window_side": "right"}'
```

`tests/unit/test_settings_editor.py`:

```python
from dataclasses import dataclass, replace
from functools import partial

import pytest

from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.settings_editor import SettingsEditor
from spare_my_eyes.settings_form import SettingsFormInput
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.settings_store import InMemorySettingsStore
from tests.fakes.startup import FakeStartupRegistration
from tests.integration.pipeline_run import CALIBRATED_SETTINGS

FORM = SettingsFormInput("right", "30", "8", "50", "0", True)


@dataclass
class EditorRig:
    editor: SettingsEditor
    controller: EyeCareController
    store: InMemorySettingsStore
    startup: FakeStartupRegistration


def make_rig(log: RecordingLogHandler, startup: FakeStartupRegistration) -> EditorRig:
    clock, notifier = FakeClock(), RecordingNotifier()
    store = InMemorySettingsStore(CALIBRATED_SETTINGS)
    factory = partial(build_coach, clock=clock, notifier=notifier, idle=FakeIdleTimeProvider())
    controller = EyeCareController(CALIBRATED_SETTINGS, store, factory, notifier, clock, log.logger)
    return EditorRig(SettingsEditor(controller, startup), controller, store, startup)


@pytest.fixture
def rig(log_recorder: RecordingLogHandler) -> EditorRig:
    return make_rig(log_recorder, FakeStartupRegistration())


def test_current_form_reflects_settings_and_startup(rig: EditorRig) -> None:
    rig.startup.enabled = True
    form = rig.editor.current_form()
    assert form.break_interval_minutes == "20"
    assert form.start_with_windows


def test_submit_valid_form_applies_settings_and_enables_startup(rig: EditorRig) -> None:
    assert rig.editor.submit(FORM) == []
    assert rig.controller.settings.break_interval_seconds == 1800.0
    assert rig.store.saved[-1].window_side == "right"
    assert rig.startup.enabled


def test_submit_unchecked_startup_disables_it(rig: EditorRig) -> None:
    rig.startup.enabled = True
    rig.editor.submit(replace(FORM, start_with_windows=False))
    assert not rig.startup.enabled


def test_submit_invalid_form_returns_problems_and_saves_nothing(rig: EditorRig) -> None:
    problems = rig.editor.submit(replace(FORM, blink_threshold="0"))
    assert len(problems) == 1
    assert rig.store.saved == []


def test_submit_startup_unavailable_leaves_registry_alone(
    log_recorder: RecordingLogHandler,
) -> None:
    rig = make_rig(log_recorder, FakeStartupRegistration(available=False))
    assert rig.editor.submit(FORM) == []
    assert not rig.startup.enabled
```

- [ ] **Step 6: Run to see them fail**

Run: `uv run pytest tests/unit/test_controller.py tests/unit/test_settings_store.py tests/unit/test_settings_editor.py -v`
Expected: FAIL with `AttributeError: 'EyeCareController' object has no attribute 'apply_settings'`, `... 'ensure_file'` and `ModuleNotFoundError: No module named 'spare_my_eyes.settings_editor'`.

- [ ] **Step 7: Implement controller, store and editor changes**

In `src/spare_my_eyes/coaching/controller.py`:

1. In `__init__`, before `self._coach = coach_factory(settings)`, add:

```python
        self._camera_status = CameraStatus.ACTIVE
```

2. Replace `on_camera_status` with:

```python
    def on_camera_status(self, status: CameraStatus) -> None:
        self._camera_status = status
        self._coach.on_camera_status(status)
        if status is not CameraStatus.ACTIVE:
            self._cancel_calibration()
            return
        if not self._settings.is_calibrated and self._calibration is None:
            self.recalibrate()
```

3. Add after `skip_break`:

```python
    def apply_settings(self, settings: Settings) -> None:
        self._coach.suspend()
        self._settings = settings
        self._store.save(settings)
        self._coach = self._coach_factory(settings)
        self._coach.on_camera_status(self._camera_status)
        log_event(self._logger, logging.INFO, "settings_applied")
```

In `src/spare_my_eyes/settings_store.py`, add to `JsonSettingsStore`:

```python
    def ensure_file(self) -> Path:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text("{}\n", encoding="utf-8")
        return self._path
```

`src/spare_my_eyes/settings_editor.py`:

```python
from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.settings_form import (
    SettingsFormError,
    SettingsFormInput,
    apply_form,
    form_input_from,
    parse_form,
)
from spare_my_eyes.system.startup_registration import StartupRegistration


class SettingsEditor:
    """Turns a submitted settings form into saved settings, live coaching and a startup entry."""

    def __init__(self, controller: EyeCareController, startup: StartupRegistration) -> None:
        self._controller = controller
        self._startup = startup

    @property
    def startup_available(self) -> bool:
        return self._startup.is_available

    def current_form(self) -> SettingsFormInput:
        enabled = self._startup.is_available and self._startup.is_enabled()
        return form_input_from(self._controller.settings, enabled)

    def submit(self, form: SettingsFormInput) -> list[str]:
        try:
            values = parse_form(form)
        except SettingsFormError as error:
            return error.problems
        self._controller.apply_settings(apply_form(self._controller.settings, values))
        self._apply_startup(values.start_with_windows)
        return []

    def _apply_startup(self, wanted: bool) -> None:
        if not self._startup.is_available:
            return
        if wanted:
            self._startup.enable()
        else:
            self._startup.disable()
```

- [ ] **Step 8: Write the failing registry tests**

`tests/integration/test_startup_registration.py`:

```python
import contextlib
import winreg
from collections.abc import Iterator
from pathlib import Path

import pytest

from spare_my_eyes.system.startup_registration import WindowsStartupRegistration

TEST_PARENT_KEY = r"Software\SpareMyEyesTests"
TEST_RUN_KEY = TEST_PARENT_KEY + r"\Run"
EXECUTABLE = Path(r"C:\Apps\Spare My Eyes\SpareMyEyes.exe")


@pytest.fixture
def registration() -> Iterator[WindowsStartupRegistration]:
    yield WindowsStartupRegistration(EXECUTABLE, key_path=TEST_RUN_KEY)
    for key in (TEST_RUN_KEY, TEST_PARENT_KEY):
        with contextlib.suppress(FileNotFoundError):
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)


def test_enable_registers_quoted_executable(registration: WindowsStartupRegistration) -> None:
    registration.enable()
    assert registration.is_enabled()
    assert registration.registered_command() == f'"{EXECUTABLE}"'


def test_disable_removes_registration(registration: WindowsStartupRegistration) -> None:
    registration.enable()
    registration.disable()
    assert not registration.is_enabled()


def test_disable_never_registered_does_nothing(registration: WindowsStartupRegistration) -> None:
    registration.disable()
    assert not registration.is_enabled()


def test_enable_running_from_source_raises_runtime_error() -> None:
    registration = WindowsStartupRegistration(None, key_path=TEST_RUN_KEY)
    assert not registration.is_available
    with pytest.raises(RuntimeError, match="installed"):
        registration.enable()
```

The tests write only under `HKEY_CURRENT_USER\Software\SpareMyEyesTests` and delete it afterwards.

- [ ] **Step 9: Implement the registry adapter**

`src/spare_my_eyes/system/startup_registration.py`:

```python
import contextlib
import sys
import winreg
from pathlib import Path
from typing import Protocol

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "SpareMyEyes"


class StartupRegistration(Protocol):
    @property
    def is_available(self) -> bool: ...

    def is_enabled(self) -> bool: ...

    def enable(self) -> None: ...

    def disable(self) -> None: ...


def installed_executable() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable)


class WindowsStartupRegistration:
    def __init__(
        self,
        executable: Path | None,
        key_path: str = RUN_KEY_PATH,
        value_name: str = RUN_VALUE_NAME,
    ) -> None:
        self._executable = executable
        self._key_path = key_path
        self._value_name = value_name

    @property
    def is_available(self) -> bool:
        return self._executable is not None

    def is_enabled(self) -> bool:
        return self.registered_command() is not None

    def registered_command(self) -> str | None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key_path) as key:
                value, _ = winreg.QueryValueEx(key, self._value_name)
        except FileNotFoundError:
            return None
        return str(value)

    def enable(self) -> None:
        if self._executable is None:
            raise RuntimeError(
                "Start with Windows needs the installed SpareMyEyes.exe; "
                f"got executable={self._executable!r} because the app runs from source"
            )
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self._key_path) as key:
            winreg.SetValueEx(key, self._value_name, 0, winreg.REG_SZ, f'"{self._executable}"')

    def disable(self) -> None:
        with (
            contextlib.suppress(FileNotFoundError),
            winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self._key_path, 0, winreg.KEY_SET_VALUE
            ) as key,
        ):
            winreg.DeleteValue(key, self._value_name)
```

`suppress(FileNotFoundError)` in `disable` is deliberate, not a swallowed error: a missing key or value already means "not registered", which is the state `disable` asks for.

Run: `uv run pytest tests/unit/test_controller.py tests/unit/test_settings_store.py tests/unit/test_settings_editor.py tests/integration/test_startup_registration.py -v`
Expected: all passed.

- [ ] **Step 10: Write the failing window tests**

`tests/integration/test_settings_window.py`:

```python
import tkinter as tk
from collections.abc import Iterator

import pytest

from spare_my_eyes.settings_form import SettingsFormInput
from spare_my_eyes.ui.settings_window import SettingsWindowOpener
from tests.fakes.settings_editor import FakeSettingsEditor

pytestmark = pytest.mark.gui

FORM = SettingsFormInput("left", "20", "8", "50", "0", False)


@pytest.fixture
def root() -> Iterator[tk.Tk]:
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


def open_window(root: tk.Tk, editor: FakeSettingsEditor, opened: list[str]) -> SettingsWindowOpener:
    opener = SettingsWindowOpener(root, editor, lambda: opened.append("file"))
    opener()
    return opener


def test_opener_first_call_shows_current_values(root: tk.Tk) -> None:
    opener = open_window(root, FakeSettingsEditor(FORM), [])
    window = opener.current
    assert window is not None and window.is_open
    assert window.break_interval.get() == "20"
    assert window.window_side.get() == "left"


def test_opener_second_call_reuses_open_window(root: tk.Tk) -> None:
    opener = open_window(root, FakeSettingsEditor(FORM), [])
    first = opener.current
    opener()
    assert opener.current is first


def test_submit_valid_form_sends_edits_and_closes(root: tk.Tk) -> None:
    editor = FakeSettingsEditor(FORM)
    window = open_window(root, editor, []).current
    assert window is not None
    window.break_interval.set("30")
    window.submit()
    assert editor.submitted[-1].break_interval_minutes == "30"
    assert not window.is_open


def test_submit_with_problems_shows_them_and_stays_open(root: tk.Tk) -> None:
    editor = FakeSettingsEditor(FORM, problems=["Camera number must be ..."])
    window = open_window(root, editor, []).current
    assert window is not None
    window.submit()
    assert window.is_open
    assert "Camera number" in str(window.problems_label.cget("text"))


def test_close_without_saving_submits_nothing(root: tk.Tk) -> None:
    editor = FakeSettingsEditor(FORM)
    window = open_window(root, editor, []).current
    assert window is not None
    window.close()
    assert editor.submitted == []
    assert not window.is_open


def test_startup_unavailable_disables_checkbox(root: tk.Tk) -> None:
    window = open_window(root, FakeSettingsEditor(FORM, startup_available=False), []).current
    assert window is not None
    assert "disabled" in window.startup_checkbox.state()


def test_open_file_button_opens_settings_file(root: tk.Tk) -> None:
    opened: list[str] = []
    window = open_window(root, FakeSettingsEditor(FORM), opened).current
    assert window is not None
    window.open_file_button.invoke()
    assert opened == ["file"]
```

Run: `uv run pytest tests/integration/test_settings_window.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.ui.settings_window'`.

- [ ] **Step 11: Implement the window**

`src/spare_my_eyes/ui/settings_window.py`:

```python
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Protocol

from spare_my_eyes.analysis.gaze import WindowSide
from spare_my_eyes.settings_form import (
    BLINK_THRESHOLD,
    BREAK_INTERVAL_MINUTES,
    CAMERA_INDEX,
    TOO_CLOSE_CM,
    FieldRange,
    SettingsFormInput,
)

PROBLEM_COLOR = "#c62828"


class SettingsEditorPort(Protocol):
    @property
    def startup_available(self) -> bool: ...

    def current_form(self) -> SettingsFormInput: ...

    def submit(self, form: SettingsFormInput) -> list[str]: ...


class SettingsWindow:
    """The everyday settings in a small form; the JSON file stays available for the rest."""

    TITLE = "Spare My Eyes settings"

    def __init__(
        self, root: tk.Tk, editor: SettingsEditorPort, open_file: Callable[[], None]
    ) -> None:
        self._editor = editor
        self._open = True
        self.window = tk.Toplevel(root)
        self.window.title(self.TITLE)
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._create_variables(editor.current_form())
        frame = ttk.Frame(self.window, padding=16)
        frame.pack(fill="both")
        self._build_fields(frame)
        self._build_buttons(frame, open_file)

    @property
    def is_open(self) -> bool:
        return self._open

    def submit(self) -> None:
        problems = self._editor.submit(self._read_form())
        if problems:
            self.problems_label.configure(text="\n".join(problems))
            return
        self.close()

    def close(self) -> None:
        self._open = False
        self.window.destroy()

    def bring_to_front(self) -> None:
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def _create_variables(self, form: SettingsFormInput) -> None:
        self.window_side = tk.StringVar(self.window, form.window_side)
        self.break_interval = tk.StringVar(self.window, form.break_interval_minutes)
        self.blink_threshold = tk.StringVar(self.window, form.blink_threshold)
        self.too_close = tk.StringVar(self.window, form.too_close_cm)
        self.camera_index = tk.StringVar(self.window, form.camera_index)
        self.start_with_windows = tk.BooleanVar(self.window, form.start_with_windows)

    def _build_fields(self, frame: ttk.Frame) -> None:
        self._build_side_row(frame)
        _spinbox_row(frame, 1, BREAK_INTERVAL_MINUTES, self.break_interval)
        _spinbox_row(frame, 2, BLINK_THRESHOLD, self.blink_threshold)
        _spinbox_row(frame, 3, TOO_CLOSE_CM, self.too_close)
        _spinbox_row(frame, 4, CAMERA_INDEX, self.camera_index, "applies after restart")
        self.startup_checkbox = ttk.Checkbutton(
            frame, text="Start with Windows", variable=self.start_with_windows
        )
        self.startup_checkbox.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        if not self._editor.startup_available:
            self.startup_checkbox.state(["disabled"])
        self.problems_label = ttk.Label(frame, foreground=PROBLEM_COLOR, wraplength=340)
        self.problems_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_side_row(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Window side").grid(row=0, column=0, sticky="w", pady=4)
        sides = ttk.Frame(frame)
        sides.grid(row=0, column=1, sticky="e")
        for side in WindowSide:
            label = side.value.capitalize()
            button = ttk.Radiobutton(sides, text=label, value=side.value, variable=self.window_side)
            button.pack(side="left")

    def _build_buttons(self, frame: ttk.Frame, open_file: Callable[[], None]) -> None:
        buttons = ttk.Frame(frame)
        buttons.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.open_file_button = ttk.Button(buttons, text="Open settings file", command=open_file)
        self.open_file_button.pack(side="left")
        ttk.Button(buttons, text="Save", command=self.submit).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=self.close).pack(side="right", padx=(0, 8))

    def _read_form(self) -> SettingsFormInput:
        return SettingsFormInput(
            window_side=self.window_side.get(),
            break_interval_minutes=self.break_interval.get(),
            blink_threshold=self.blink_threshold.get(),
            too_close_cm=self.too_close.get(),
            camera_index=self.camera_index.get(),
            start_with_windows=self.start_with_windows.get(),
        )


class SettingsWindowOpener:
    def __init__(
        self, root: tk.Tk, editor: SettingsEditorPort, open_file: Callable[[], None]
    ) -> None:
        self._root = root
        self._editor = editor
        self._open_file = open_file
        self._window: SettingsWindow | None = None

    @property
    def current(self) -> SettingsWindow | None:
        return self._window

    def __call__(self) -> None:
        if self._window is not None and self._window.is_open:
            self._window.bring_to_front()
            return
        self._window = SettingsWindow(self._root, self._editor, self._open_file)


def _spinbox_row(
    frame: ttk.Frame, row: int, field: FieldRange, variable: tk.StringVar, note: str = ""
) -> None:
    label = f"{field.label} ({note})" if note else field.label
    ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
    spinbox = ttk.Spinbox(
        frame, from_=field.minimum, to=field.maximum, textvariable=variable, width=6
    )
    spinbox.grid(row=row, column=1, sticky="e")
```

- [ ] **Step 12: Run to see them pass**

Run: `uv run ruff format . && uv run ruff check --fix . && uv run pytest tests/unit tests/integration/test_settings_window.py tests/integration/test_startup_registration.py -v && uv run mypy`
Expected: all passed, mypy clean.

- [ ] **Step 13: Commit**

```bash
git add src/spare_my_eyes/settings_form.py src/spare_my_eyes/settings_editor.py src/spare_my_eyes/system/startup_registration.py src/spare_my_eyes/ui/settings_window.py src/spare_my_eyes/coaching/controller.py src/spare_my_eyes/settings_store.py tests/fakes/startup.py tests/fakes/settings_editor.py tests/unit/test_settings_form.py tests/unit/test_settings_editor.py tests/unit/test_controller.py tests/unit/test_settings_store.py tests/integration/test_startup_registration.py tests/integration/test_settings_window.py
git commit -m "feat: add settings window with live apply and start-with-Windows

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 23: App runtime, composition root and smoke test

**Files:**
- Create: `src/spare_my_eyes/paths.py`, `src/spare_my_eyes/app_runtime.py`, `src/spare_my_eyes/ui/tk_main_loop.py`, `src/spare_my_eyes/app.py`, `src/spare_my_eyes/__main__.py`
- Create: `tests/fakes/runtime.py`
- Test: `tests/unit/test_paths.py`, `tests/unit/test_app_runtime.py`, `tests/unit/test_app_options.py`, `tests/integration/test_app_smoke.py`

**Interfaces:**
- Consumes: everything above, including `SettingsEditor`, `SettingsWindowOpener`, `WindowsStartupRegistration`, `installed_executable`, `JsonSettingsStore.ensure_file` (Task 22).
- Produces:
  - `AppPaths(data_dir: Path)` with `settings_file`, `log_dir`; `default_data_dir(environment: Mapping[str, str]) -> Path` (raises `RuntimeError` naming the value when `APPDATA` is missing).
  - `UserCommand` (StrEnum): `PAUSE_FOR_HOUR`, `START_BREAK`, `SNOOZE_BREAK`, `SKIP_BREAK`, `RECALIBRATE`, `OPEN_SETTINGS`, `QUIT`.
  - Protocols `MainLoop` (`schedule(delay_ms, callback)`, `run()`, `stop()`), `CaptureControl` (`start`, `stop`, `suspend`, `resume`, `is_suspended`), `TrayLifecycle` (`start`, `stop`).
  - `RuntimeChannels(capture: queue.Queue[CaptureMessage], commands: queue.Queue[UserCommand])`.
  - `AppRuntime(loop, controller, worker, tray, channels, open_settings: Callable[[], None], clock, logger)` with `run(exit_after_seconds: float | None)`, `pump()`, `quit()`. Logs `tray_started`, `app_stopped`, `main_loop_error`.
  - `TkMainLoop(root: tk.Tk)` implementing `MainLoop`.
  - `LaunchOptions(data_dir: Path, scripted_camera: str | None, exit_after_seconds: float | None)`; `parse_options(argv, environment) -> LaunchOptions`; `main(argv: Sequence[str] | None = None) -> int`. Logs `app_started`, `app_crashed`.
  - Fakes: `FakeMainLoop`, `FakeCaptureWorker`, `RecordingCallback` (`.calls: int`), `FailingCallback`.

Tray → Settings opens the settings window from Task 22. Its "Open settings file" button opens `settings.json` in the default editor for the advanced keys.

- [ ] **Step 1: Write the fakes**

`tests/fakes/runtime.py`:

```python
from collections.abc import Callable


class FakeMainLoop:
    def __init__(self) -> None:
        self.scheduled: list[tuple[int, Callable[[], None]]] = []
        self.running = False
        self.stopped = False

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> None:
        self.scheduled.append((delay_ms, callback))

    def run(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.stopped = True


class FakeCaptureWorker:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.resumes = 0
        self._suspended = False

    @property
    def is_suspended(self) -> bool:
        return self._suspended

    def start(self) -> None:
        self.started = True

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self.stopped = True

    def suspend(self) -> None:
        self._suspended = True

    def resume(self) -> None:
        self._suspended = False
        self.resumes += 1


class RecordingCallback:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


class FailingCallback:
    def __call__(self) -> None:
        raise OSError("Settings window could not be created: no display available")
```

- [ ] **Step 2: Write the failing tests**

`tests/unit/test_paths.py`:

```python
from pathlib import Path

import pytest

from spare_my_eyes.paths import AppPaths, default_data_dir


def test_default_data_dir_appdata_set_returns_spare_my_eyes_folder() -> None:
    assert default_data_dir({"APPDATA": "C:/Users/me/AppData/Roaming"}) == Path(
        "C:/Users/me/AppData/Roaming/SpareMyEyes"
    )


def test_default_data_dir_appdata_missing_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="APPDATA"):
        default_data_dir({})


def test_app_paths_layout_puts_settings_and_logs_in_data_dir() -> None:
    paths = AppPaths(Path("D:/data"))
    assert paths.settings_file == Path("D:/data/settings.json")
    assert paths.log_dir == Path("D:/data/logs")
```

`tests/unit/test_app_options.py`:

```python
from pathlib import Path

import pytest

from spare_my_eyes.app import parse_options

ENVIRONMENT = {"APPDATA": "C:/Users/me/AppData/Roaming"}


def test_parse_options_no_arguments_uses_appdata_and_real_camera() -> None:
    options = parse_options([], ENVIRONMENT)
    assert options.data_dir == Path("C:/Users/me/AppData/Roaming/SpareMyEyes")
    assert options.scripted_camera is None
    assert options.exit_after_seconds is None


def test_parse_options_all_flags_are_read() -> None:
    argv = ["--scripted-camera", "normal", "--exit-after", "6", "--data-dir", "D:/tmp"]
    options = parse_options(argv, ENVIRONMENT)
    assert options.scripted_camera == "normal"
    assert options.exit_after_seconds == 6.0
    assert options.data_dir == Path("D:/tmp")


def test_parse_options_unknown_scenario_exits_with_usage_error() -> None:
    with pytest.raises(SystemExit):
        parse_options(["--scripted-camera", "nonexistent"], ENVIRONMENT)
```

`tests/unit/test_app_runtime.py`:

```python
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
    runtime = AppRuntime(
        loop, controller, worker, tray, channels, open_settings, clock, log.logger
    )
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
```

`tests/integration/test_app_smoke.py`:

```python
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
        sys.executable, "-m", "spare_my_eyes",
        "--scripted-camera", "normal", "--exit-after", "6", "--data-dir", str(tmp_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stderr
    entries = read_log_entries(tmp_path)
    events = [entry["event"] for entry in entries]
    assert "tray_started" in events
    assert any(
        entry["event"] == "notification_shown" and entry.get("kind") == "break"
        for entry in entries
    )
    assert events[-1] == "app_stopped"
```

- [ ] **Step 3: Run to see them fail**

Run: `uv run pytest tests/unit/test_paths.py tests/unit/test_app_options.py tests/unit/test_app_runtime.py tests/integration/test_app_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError` for `spare_my_eyes.paths`, `spare_my_eyes.app`, `spare_my_eyes.app_runtime`.

- [ ] **Step 4: Implement paths**

`src/spare_my_eyes/paths.py`:

```python
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_FOLDER_NAME = "SpareMyEyes"


@dataclass(frozen=True, slots=True)
class AppPaths:
    data_dir: Path

    @property
    def settings_file(self) -> Path:
        return self.data_dir / "settings.json"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"


def default_data_dir(environment: Mapping[str, str]) -> Path:
    appdata = environment.get("APPDATA")
    if not appdata:
        raise RuntimeError(
            f"APPDATA is not set (got {appdata!r}); expected a Windows profile path such as "
            r"C:\Users\me\AppData\Roaming"
        )
    return Path(appdata) / APP_FOLDER_NAME
```

- [ ] **Step 5: Implement the runtime**

`src/spare_my_eyes/ui/tk_main_loop.py`:

```python
import tkinter as tk
from collections.abc import Callable


class TkMainLoop:
    def __init__(self, root: tk.Tk) -> None:
        self._root = root

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> None:
        self._root.after(delay_ms, callback)

    def run(self) -> None:
        self._root.mainloop()

    def stop(self) -> None:
        self._root.quit()
```

`src/spare_my_eyes/app_runtime.py`:

```python
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
```

- [ ] **Step 6: Implement the composition root**

`src/spare_my_eyes/app.py`:

```python
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
from spare_my_eyes.coaching.notifier import Notifier
from spare_my_eyes.coaching.factory import build_coach
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
```

`src/spare_my_eyes/__main__.py`:

```python
from spare_my_eyes.app import main

raise SystemExit(main())
```

- [ ] **Step 7: Run to see them pass**

Run: `uv run ruff format . && uv run ruff check --fix . && uv run pytest -v && uv run mypy`
Expected: all passed (fixture-dependent MediaPipe tests may be skipped), mypy clean. The smoke test opens a tray icon and a break card for about 6 seconds.

- [ ] **Step 8: Try the app by hand**

```bash
uv run python -m spare_my_eyes --scripted-camera low-blink-rate --data-dir "$TEMP/sme-demo"
```

Expected:
- The calibration card appears for 20 s, fed by the scripted face.
- After about 2 minutes, a "Blink" overlay appears bottom-right without taking focus from your editor.
- Tray → Settings opens the form. Change "Break every" to 5 and press Save: the window closes, and `$TEMP/sme-demo/settings.json` now has `"break_interval_seconds": 300.0`. "Start with Windows" is disabled, because the app runs from source.
- Quit from the tray menu.

Then run `uv run python -m spare_my_eyes` with the real webcam and follow the calibration prompts.

- [ ] **Step 9: Commit**

```bash
git add src/spare_my_eyes/paths.py src/spare_my_eyes/app_runtime.py src/spare_my_eyes/ui/tk_main_loop.py src/spare_my_eyes/app.py src/spare_my_eyes/__main__.py tests/fakes/runtime.py tests/unit/test_paths.py tests/unit/test_app_options.py tests/unit/test_app_runtime.py tests/integration/test_app_smoke.py
git commit -m "feat: wire the app together with a Tk main loop and smoke test

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 24: CI, app icon, installer and release packaging

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `packaging/launcher.py`, `packaging/installer.iss`, `src/spare_my_eyes/ui/app_icon.py`
- Modify: `.gitignore` (add `packaging/SpareMyEyes.ico`)
- Test: `tests/unit/test_app_icon.py`

**Interfaces:**
- Consumes: `spare_my_eyes.app.main`, `status_icon_image` (Task 21), `python -m spare_my_eyes.model_asset`, `RUN_VALUE_NAME = "SpareMyEyes"` (Task 22).
- Produces:
  - `write_app_icon(destination: Path) -> None` (multi-size `.ico`); `python -m spare_my_eyes.ui.app_icon <path>`.
  - Green CI on every push and pull request.
  - On each `v*` tag, two release assets: `SpareMyEyes-Setup-<version>.exe` and `SpareMyEyes-<tag>-portable.zip`.

The installer is per-user (`PrivilegesRequired=lowest`, installs under `%LOCALAPPDATA%\Programs\Spare My Eyes`, no admin prompt). Its optional "start when I sign in" writes the same `HKCU\...\Run\SpareMyEyes` value as the settings window, so the two always agree. The uninstaller stops the app and removes that value. It keeps `%APPDATA%\SpareMyEyes` (settings and logs), so a reinstall keeps the calibration. The `AppId` GUID below is fixed forever: changing it would make upgrades install side by side.

Cost: GitHub Actions and Inno Setup are free. No code-signing certificate is used, so Windows SmartScreen shows "Windows protected your PC / unknown publisher" on first run; the README explains "More info → Run anyway".

- [ ] **Step 1: Write the failing icon test**

`tests/unit/test_app_icon.py`:

```python
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
```

Run: `uv run pytest tests/unit/test_app_icon.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spare_my_eyes.ui.app_icon'`.

- [ ] **Step 2: Implement the icon writer**

`src/spare_my_eyes/ui/app_icon.py`:

```python
import sys
from pathlib import Path

from PIL import Image

from spare_my_eyes.coaching.notifier import TrayStatus
from spare_my_eyes.ui.tray_icon import status_icon_image

ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def write_app_icon(destination: Path) -> None:
    large = status_icon_image(TrayStatus.MONITORING).resize(
        (256, 256), Image.Resampling.LANCZOS
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    large.save(destination, format="ICO", sizes=ICON_SIZES)


if __name__ == "__main__":
    write_app_icon(Path(sys.argv[1]))
```

Add `packaging/SpareMyEyes.ico` to `.gitignore`.

Run: `uv run pytest tests/unit/test_app_icon.py -v`
Expected: 1 passed.

- [ ] **Step 3: Write the CI workflow**

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  check:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv python install 3.12
      - run: uv sync --locked
      - run: uv run python -m spare_my_eyes.model_asset
      - run: uv run ruff format --check .
      - run: uv run ruff check .
      - run: uv run mypy
      - run: uv run pytest
```

- [ ] **Step 4: Write the launcher and the installer script**

`packaging/launcher.py`:

```python
from spare_my_eyes.app import main

raise SystemExit(main())
```

`packaging/installer.iss`:

```ini
#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif

[Setup]
AppId={{D004EF3B-63BD-4160-90EF-FB4C3BA8D6F5}
AppName=Spare My Eyes
AppVersion={#AppVersion}
AppPublisher=Spare My Eyes contributors
DefaultDirName={autopf}\Spare My Eyes
DefaultGroupName=Spare My Eyes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=SpareMyEyes-Setup-{#AppVersion}
SetupIconFile=SpareMyEyes.ico
UninstallDisplayIcon={app}\SpareMyEyes.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=force

[Tasks]
Name: "startup"; Description: "Start Spare My Eyes when I sign in to Windows"; GroupDescription: "Startup:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\SpareMyEyes\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Spare My Eyes"; Filename: "{app}\SpareMyEyes.exe"
Name: "{autodesktop}\Spare My Eyes"; Filename: "{app}\SpareMyEyes.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SpareMyEyes"; ValueData: """{app}\SpareMyEyes.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\SpareMyEyes.exe"; Description: "Start Spare My Eyes now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM SpareMyEyes.exe /F"; Flags: runhidden; RunOnceId: "StopSpareMyEyes"
```

- [ ] **Step 5: Build the app and the installer locally**

Install Inno Setup 6 once (free): `winget install --id JRSoftware.InnoSetup -e`. Then:

```bash
uv run python -m spare_my_eyes.ui.app_icon packaging/SpareMyEyes.ico
uv run pyinstaller --noconfirm --windowed --name SpareMyEyes --icon packaging/SpareMyEyes.ico --collect-all mediapipe --add-data "src/spare_my_eyes/assets/face_landmarker.task;spare_my_eyes/assets" packaging/launcher.py
./dist/SpareMyEyes/SpareMyEyes.exe --scripted-camera normal --exit-after 5 --data-dir "$TEMP/sme-package"
"/c/Program Files (x86)/Inno Setup 6/ISCC.exe" /DAppVersion=0.1.0 packaging/installer.iss
```

Expected:
- The exe runs for about 5 s and exits, and `$TEMP/sme-package/logs/spare-my-eyes.log` ends with `app_stopped`. If it shows `app_crashed` with a missing module instead, add the matching `--collect-all` or `--hidden-import` flag here and in `release.yml`.
- `dist/SpareMyEyes-Setup-0.1.0.exe` exists.

Run the installer by hand once:
1. Confirm there is no admin prompt.
2. Keep "Start when I sign in" checked and finish with "Start Spare My Eyes now".
3. Check that the tray icon appears, Tray → Settings shows "Start with Windows" checked and enabled, and Windows "Settings → Apps → Startup" lists Spare My Eyes.
4. Uninstall from "Settings → Apps".
5. Check that the app stops, the startup entry is gone, and `%APPDATA%\SpareMyEyes` is still there.

- [ ] **Step 6: Write the release workflow**

`.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write

jobs:
  build:
    runs-on: windows-latest
    env:
      INNO_COMPILER: C:\Program Files (x86)\Inno Setup 6\ISCC.exe
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv python install 3.12
      - run: uv sync --locked
      - run: uv run python -m spare_my_eyes.model_asset
      - run: uv run pytest
      - run: uv run python -m spare_my_eyes.ui.app_icon packaging/SpareMyEyes.ico
      - name: Build one-folder app
        run: >
          uv run pyinstaller --noconfirm --windowed --name SpareMyEyes
          --icon packaging/SpareMyEyes.ico
          --collect-all mediapipe
          --add-data "src/spare_my_eyes/assets/face_landmarker.task;spare_my_eyes/assets"
          packaging/launcher.py
      - name: Smoke-test the packaged app
        shell: pwsh
        run: |
          $data = Join-Path $env:RUNNER_TEMP "sme-smoke"
          New-Item -ItemType Directory -Force $data | Out-Null
          '{"open_ear_baseline": 0.3, "focal_scale": 660.0}' | Set-Content -Encoding utf8 (Join-Path $data "settings.json")
          $process = Start-Process -FilePath "dist/SpareMyEyes/SpareMyEyes.exe" -ArgumentList "--scripted-camera normal --exit-after 5 --data-dir `"$data`"" -Wait -PassThru
          if ($process.ExitCode -ne 0) { Get-Content (Join-Path $data "logs/spare-my-eyes.log"); exit 1 }
      - name: Install Inno Setup
        run: choco install innosetup --no-progress -y
      - name: Build installer
        shell: pwsh
        run: |
          $version = "${{ github.ref_name }}".TrimStart("v")
          & $env:INNO_COMPILER "/DAppVersion=$version" packaging/installer.iss
          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
      - name: Smoke-test install and uninstall
        shell: pwsh
        run: |
          $version = "${{ github.ref_name }}".TrimStart("v")
          $target = Join-Path $env:RUNNER_TEMP "sme-install"
          Start-Process "dist/SpareMyEyes-Setup-$version.exe" -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /TASKS=`"`" /DIR=`"$target`"" -Wait
          if (-not (Test-Path "$target/SpareMyEyes.exe")) { Write-Error "Installer did not create $target/SpareMyEyes.exe"; exit 1 }
          Start-Process "$target/unins000.exe" -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES" -Wait
          for ($i = 0; $i -lt 30 -and (Test-Path "$target/SpareMyEyes.exe"); $i++) { Start-Sleep -Seconds 1 }
          if (Test-Path "$target/SpareMyEyes.exe") { Write-Error "Uninstaller left $target/SpareMyEyes.exe"; exit 1 }
      - name: Zip portable build
        shell: pwsh
        run: Compress-Archive -Path dist/SpareMyEyes -DestinationPath "dist/SpareMyEyes-${{ github.ref_name }}-portable.zip"
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/SpareMyEyes-Setup-*.exe
            dist/SpareMyEyes-${{ github.ref_name }}-portable.zip
```

The uninstaller copies itself to a temp folder and returns right away. The wait loop gives it up to 30 s to finish deleting files.

- [ ] **Step 7: Run all checks**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest`
Expected: everything passes.

- [ ] **Step 8: Commit**

```bash
git add .github packaging/launcher.py packaging/installer.iss src/spare_my_eyes/ui/app_icon.py tests/unit/test_app_icon.py .gitignore
git commit -m "ci: add CI, per-user installer and release packaging

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 25: README and manual checklist

**Files:**
- Create: `docs/manual-test-checklist.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the installer (Task 24), the settings window (Task 22), the tray menu (Task 21).
- Produces: user-facing documentation for installing, using and building the app.

- [ ] **Step 1: Write the manual checklist**

`docs/manual-test-checklist.md`:

```markdown
# Manual test checklist

Run these with a real webcam before each release. Note the date, webcam model and result.

## Install
- [ ] The installer runs without an admin prompt. SmartScreen "More info → Run anyway" works.
- [ ] Start menu has "Spare My Eyes". The desktop shortcut exists only if chosen.
- [ ] "Start when I sign in" makes the app start after sign-out/sign-in.
- [ ] Installing a newer version over an older one closes the running app and keeps the calibration.
- [ ] Uninstall stops the app and removes the startup entry; `%APPDATA%\SpareMyEyes` remains.

## Calibration
- [ ] First launch shows the calibration card and completes in about 20 s.
- [ ] `settings.json` afterwards contains `open_ear_baseline` and `focal_scale`.
- [ ] Tray → Recalibrate runs it again and updates both values.

## Settings window
- [ ] Tray → Settings opens one window; choosing it again brings the same window to the front.
- [ ] Typing 200 in "Break every" and pressing Save shows the problem and keeps the window open.
- [ ] Changing "Break every" to 5 and saving: a break card appears after about 5 minutes, without
      restarting.
- [ ] "Start with Windows" on/off matches Windows "Settings → Apps → Startup".
- [ ] "Open settings file" opens `settings.json` in the default editor.

## Blink detection
- [ ] Stare at the screen without blinking for 2 minutes: the "Blink" overlay appears bottom-right.
- [ ] Two deliberate full blinks hide it.
- [ ] Half-blinks (eyelids barely moving) for 2 minutes produce "Blink slowly, close fully".
- [ ] With glasses on, blink count over 1 minute roughly matches a manual count (within ±20%).
- [ ] In dim lighting the app shows nothing rather than false alerts.

## Distance
- [ ] Lean in to about 40 cm for 30 s: "Move back a little" appears.
- [ ] Sit back past about 55 cm: it disappears.

## Break
- [ ] Turning toward the configured window side advances "Look out the window"; the other side does not.
- [ ] Five slow full blinks finish the break.
- [ ] Snooze and Skip work; leaving the card alone for 2 minutes closes it.

## Focus and windows
- [ ] While typing in another app, no overlay or card steals keyboard focus.
- [ ] Overlays do not appear in Alt+Tab.
- [ ] With display scaling at 150%, overlays sit fully on screen.
- [ ] On a multi-monitor setup, overlays appear on the primary monitor.

## Camera problems
- [ ] Start a Teams/Zoom call using the camera: the tray turns amber (paused) and no alerts appear.
- [ ] Unplug the webcam: the tray turns gray within a minute; plug it back: monitoring resumes within a minute.
- [ ] Pause for 1 hour: the webcam light turns off.

## Resources
- [ ] Task Manager shows CPU use for SpareMyEyes. Record the value at 20 fps. If it is above 10% of
      one core, try `"frames_per_second": 15` and record again.
- [ ] Memory stays stable over 1 hour (record start and end).

## Privacy
- [ ] No files besides `settings.json` and `logs/` exist under `%APPDATA%\SpareMyEyes`.
- [ ] Windows "Privacy & security → Camera" shows only Spare My Eyes using the camera while it runs.
```

- [ ] **Step 2: Write the README**

`README.md`:

~~~~markdown
# Spare My Eyes

A free Windows tray app that watches how you actually use your eyes and nudges you only when
they need it, instead of firing reminders on a fixed timer.

## What it does

- **Blink monitoring.** Counts your blinks and tells complete from incomplete ones. If you blink
  fewer than 8 times a minute for 2 minutes, a small "Blink" note appears in the corner. Two full
  blinks make it go away.
- **Screen distance.** Estimates how far you sit from the screen from the size of your iris. If you
  stay closer than 50 cm for 30 seconds, it asks you to move back.
- **Verified breaks.** Every 20 minutes of screen time, a card asks you to look out the window for
  20 seconds (the camera checks that you turned your head) and then do 5 slow, full blinks.
- **Works without a camera.** If the webcam is missing or busy, breaks still come, timed by your
  keyboard and mouse activity.

## Why not a timer

Fixed 20-20-20 reminders have weak evidence. The main cause of digital eye strain is blinking
less, and less completely, while looking at a screen. Blink training has improved symptoms in a
randomized trial. See the design document in `docs/superpowers/specs/` for sources.

## Privacy

Everything runs on your computer. Each webcam frame is processed in memory and discarded right
away. No image is ever saved or sent anywhere. There is no account, telemetry or network access
after installation. Pausing from the tray turns the camera off.

## Install

1. Download `SpareMyEyes-Setup-<version>.exe` from the [Releases](../../releases) page.
2. Run it. No administrator rights are needed. Windows may show "Windows protected your PC"
   because the installer is not code-signed: click **More info → Run anyway**.
3. Keep **Start Spare My Eyes when I sign in to Windows** checked if you want it running every day.

On first launch it calibrates for about 20 seconds: look at the screen normally, then sit at
arm's length when asked.

To uninstall, use Windows **Settings → Apps → Installed apps → Spare My Eyes**. Your settings in
`%APPDATA%\SpareMyEyes` are kept in case you reinstall; delete that folder to remove them.

Prefer not to install? Download `SpareMyEyes-<version>-portable.zip`, unzip it anywhere and run
`SpareMyEyes.exe`.

## Using it

Right-click the eye icon in the system tray:

- **Pause for 1 hour**: stops all reminders and turns the camera off.
- **Start break now**
- **Recalibrate**: run calibration again, for example after moving your webcam.
- **Settings**: opens the settings window.
- **Quit**

The icon is green while monitoring, amber when paused or the camera is busy, gray without a
camera, and blue while calibrating. Hover over it to see your current blink rate.

## Settings

The settings window covers the everyday options and applies them right away:

| Option | Default |
|---|---|
| Window side (where to look during breaks) | Left |
| Break every (minutes) | 20 |
| Blink alert below (blinks/min) | 8 |
| Too close below (cm) | 50 |
| Camera number (applies after restart) | 0 |
| Start with Windows | as chosen in the installer |

**Open settings file** in the same window opens `%APPDATA%\SpareMyEyes\settings.json` for the
advanced options, such as `frames_per_second` (lower it if CPU use is too high), cooldowns and
break targets. Changes made in the file apply on the next start. A wrong value is ignored and
logged, and its default is used.

## Limitations

- Windows 10/11 (64-bit) only.
- Blink completeness is an estimate: at 20 frames per second the deepest point of a blink can
  fall between frames. Blink rate is the more reliable signal.
- Some webcams can be used by only one app at a time. While a video call uses the camera,
  Spare My Eyes pauses measurement and retries every minute.
- Distance depends on calibration. Recalibrate after moving the webcam or changing monitors.

## Development

```bash
uv sync
uv run python -m spare_my_eyes.model_asset
uv run pytest
uv run python -m spare_my_eyes --scripted-camera low-blink-rate --data-dir "%TEMP%\sme-demo"
```

`--scripted-camera` replays a scripted face instead of the webcam. Scenarios: `normal`,
`low-blink-rate`, `incomplete-blinks`, `too-close`, `away`. Real-webcam checks are in
`docs/manual-test-checklist.md`. Pushing a `v*` tag builds the installer and the portable zip
and attaches them to a GitHub Release.

## License

MIT. The MediaPipe Face Landmarker model is © Google, Apache 2.0.
~~~~

- [ ] **Step 3: Run the full suite one last time**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest`
Expected: everything passes, with fixture-dependent tests skipped only where `tests/fixtures/CREDITS.md` lists a missing case.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/manual-test-checklist.md
git commit -m "docs: add README and manual test checklist

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

Pushing to GitHub and tagging `v0.1.0` are left to the user. Both are outward-facing; ask before doing either.
