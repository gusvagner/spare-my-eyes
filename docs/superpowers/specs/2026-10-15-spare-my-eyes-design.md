# Spare My Eyes — Design

Date: 2026-10-15
Status: Draft for review

## 1. Purpose

Spare My Eyes is a free, open-source Windows tray app that reduces digital eye strain by
watching how you actually use your eyes, instead of firing reminders on a fixed timer.

It is built first for the author's own daily use and published as a public GitHub
repository, so installation and documentation must be simple enough for other people.

### Why not another timer app

Existing break reminders (Stretchly, EyeLeo, Workrave, Save My Eyes) remind you on a fixed
schedule. The research points elsewhere:

- The 20-20-20 rule has weak evidence. Reminders reduced symptoms during use, but symptoms
  returned a week after stopping (Aston, 2022), and a SUNY study found little benefit.
- The main mechanism is reduced and incomplete blinking. People blink ~5–7 times/min at a
  screen, and incomplete blinks rise from ~4% on paper to ~7% on a screen.
- Cognitive load cuts blink rate by ~25%, independent of display type.
- Blink training improved blink behavior and ocular surface measures in a 2025 randomized
  trial (40 participants, smartphone app, 30 days).
- Viewing distance and lighting reduce symptoms more than blink rate alone.

### Success criteria

1. Blink rate and blink completeness are measured from the webcam, locally, in real time.
2. A subtle nudge appears only when the user is actually blinking too little.
3. The user is warned when sitting too close to the screen.
4. Breaks are verified: the user really looks out the window and really blinks fully.
5. No image ever leaves the process or touches the disk.
6. CPU use stays low enough to run all day.
7. The whole behavior is covered by automated unit and integration tests that run with one
   command and in CI.

## 2. Scope

### In scope (v1)

1. **Blink monitoring** — rate and complete/incomplete classification, adaptive nudge.
2. **Verified blink training** — slow, complete blinks confirmed by the camera.
3. **Screen distance alert** — distance estimated from iris size.
4. **Verified window break** — head pose confirms the user looked toward the window.
5. **Settings window** — the everyday settings edited in a small form, applied without restart.
6. **Windows installer** — per-user setup with Start menu shortcut, optional start with
   Windows, and uninstaller.

### Out of scope (v1)

- Automatic monitor brightness control (DDC/CI).
- Symptom diary and history reports.
- macOS and Linux.
- Any cloud service, telemetry or account.

## 3. Constraints

- Windows 10/11, Python 3.12.
- All processing local. Frames are processed in memory and discarded immediately.
- Code, README and UI in English. MIT license.
- Third-party libraries are wrapped behind interfaces owned by the project and injected
  through constructors.

## 4. Architecture

A single Python process with three parts.

```
 ┌──────────────── capture thread ────────────────┐      ┌──── main thread ────┐
 │ FrameSource ──► FaceLandmarkDetector ──► FaceSample ──►│ analyzers ► Coach    │
 │ (OpenCV)        (MediaPipe)                     queue  │        │            │
 └────────────────────────────────────────────────┘      │        ▼            │
                                                          │ UI: tray, overlays  │
                                                          └─────────────────────┘
```

### 4.1 Capture (worker thread)

- `OpenCvFrameSource` reads the webcam at 640×480, ~20 fps (configurable).
  20 fps is needed because a blink lasts ~100–300 ms.
- `MediaPipeFaceLandmarker` runs the MediaPipe Face Landmarker task (face + iris landmarks
  and facial transformation matrix) and produces a `FaceSample`:

| Field | Meaning |
|---|---|
| `timestamp` | Monotonic seconds |
| `face_present` | A face was detected with sufficient confidence |
| `left_ear`, `right_ear` | Eye aspect ratio per eye |
| `iris_diameter_px` | Mean iris diameter in pixels |
| `head_yaw_degrees` | Head rotation; negative = user's left |

- The frame is dropped as soon as the sample is produced. Nothing is stored.
- Samples go to the main thread through a thread-safe queue.

### 4.2 Analyzers (pure, no I/O)

Each analyzer consumes `FaceSample`s and emits typed events. None of them touches the camera,
clock or UI, so each can be tested in isolation.

| Analyzer | Responsibility |
|---|---|
| `BlinkDetector` | Turns the EAR curve into `Blink` events (complete / incomplete / deliberate closure). |
| `BlinkRateMonitor` | Sliding 2-min window; reports low rate and high incomplete ratio. |
| `ScreenDistanceEstimator` | Converts iris diameter to centimeters; reports too-close with hysteresis. |
| `WindowGazeDetector` | Reports whether the head is turned toward the configured window side. |
| `PresenceTracker` | Present / absent based on face detection over time. |

### 4.3 Coach and UI (main thread)

- `Coach` combines analyzer outputs with the clock and settings and decides what the UI
  should show. It owns cooldowns and the break schedule.
- `BreakSession` is the state machine of a single combined break.
- UI is a thin layer driven by the Coach through a `Notifier` interface:
  - `BlinkOverlay` — small borderless, semi-transparent tkinter window, bottom-right,
    never takes focus.
  - `BreakCard` — non-blocking card near the screen center with progress and buttons.
  - `TrayIcon` — pystray icon running detached; tkinter owns the main loop.

### 4.4 Interfaces and test doubles

| Interface | Production | Test double |
|---|---|---|
| `FrameSource` | `OpenCvFrameSource` | `FailingFrameSource`, `StillImageFrameSource` |
| `FaceLandmarkDetector` | `MediaPipeFaceLandmarker` | — (always real; covered by MediaPipe integration tests) |
| `FaceSampleSource` | `CameraFaceSampleSource` (FrameSource + FaceLandmarkDetector) | `ScriptedFaceSampleSource` |
| `Clock` | `MonotonicClock` | `FakeClock` |
| `Notifier` | `TkNotifier` | `RecordingNotifier` |
| `IdleTimeProvider` | `WindowsIdleTimeProvider` (GetLastInputInfo) | `FakeIdleTimeProvider` |
| `SettingsStore` | `JsonSettingsStore` | `InMemorySettingsStore` |

## 5. Behavior

### 5.1 Calibration

Runs on first launch and from the tray menu (~20 s).

1. The user looks at the screen normally for 10 s. The median EAR becomes `open_ear_baseline`.
2. The user sits at arm's length (~60 cm). The median iris diameter at that distance sets
   the camera's focal scale for distance estimation.

Results are saved in settings. Until calibration exists, the app runs calibration before
monitoring.

### 5.2 Blink detection

| Rule | Value |
|---|---|
| Blink starts | EAR < 80% of baseline |
| Blink ends | EAR back above 80% of baseline |
| Counted as spontaneous blink | Duration ≤ 500 ms |
| Complete | Minimum EAR during the blink < 40% of baseline |
| Incomplete | Minimum EAR stays ≥ 40% of baseline |
| Deliberate closure | Duration > 500 ms; not counted in the spontaneous rate |

EAR is the mean of both eyes. Completeness is an estimate: at 20 fps the deepest point of a
blink can fall between frames. Blink rate is the more reliable signal.

### 5.3 Blink nudge

- Trigger: rate < 8 blinks/min over the last 2 minutes of presence.
- Text: "Blink" by default; "Blink slowly, close fully" when incomplete blinks > 30% of the
  window.
- Hides after 2 complete blinks or 8 s, whichever comes first.
- Cooldown: 3 minutes after hiding.

### 5.4 Distance alert

- Trigger: estimated distance < 50 cm continuously for 30 s.
- Text: "Move back a little".
- Hides when distance > 55 cm (hysteresis).
- Cooldown: 5 minutes.

### 5.5 Combined break

- Screen-time counter accumulates while present. Absences < 5 min pause it; absences
  ≥ 5 min reset it.
- At 20 minutes, the `BreakCard` appears (non-blocking):
  1. **Look out the window** — progress advances only while head yaw is ≥ 25° toward the
     configured window side (default: left), until 20 s accumulate.
  2. **5 slow, complete blinks** — each counts when EAR drops below 40% of baseline for
     ≥ 300 ms.
- Buttons: **Snooze 5 min** and **Skip**.
- No interaction for 2 minutes closes the card and records the break as skipped.
- Completing, skipping or timing out resets the screen-time counter.

### 5.6 Tray

- Icon color reflects state: monitoring, paused, no camera.
- Tooltip shows the current blink rate.
- Menu: Pause for 1 hour, Start break now, Recalibrate, Settings, Quit.

### 5.7 Settings

Stored as JSON in `%APPDATA%\SpareMyEyes\settings.json`: window side, thresholds, intervals,
fps, calibration values. Defaults live in code; the file only holds overrides.

### 5.8 Settings window

Opened from the tray menu (Settings). One instance at a time.

| Field | Range | Setting |
|---|---|---|
| Window side | Left / Right | `window_side` |
| Break every (minutes) | 5–120 | `break_interval_seconds` |
| Blink alert below (blinks/min) | 3–20 | `blink_rate_threshold_per_minute` |
| Too close below (cm) | 30–80 | `too_close_cm` (clear distance = value + 5 cm) |
| Camera number | 0–9 | `camera_index` (applies after restart) |
| Start with Windows | on / off | `HKCU\...\CurrentVersion\Run\SpareMyEyes` (installed app only) |

- **Save** validates every field, lists all problems at once, and keeps the window open until
  they are fixed. On success it saves, rebuilds the coaching with the new values (the
  screen-time counter restarts) and closes.
- **Cancel** closes without changes. **Open settings file** opens the JSON for the other keys.

## 6. Error handling

| Situation | Behavior |
|---|---|
| No webcam or open failure | Gray icon; retry every 60 s. Breaks fall back to unverified time-based reminders using Windows idle time for presence. |
| Camera in use by another app | Pause measurement silently; retry every 60 s. |
| No face or poor lighting | Discard samples; no alerts. After 1 min without a face, treat as absent. |
| Missing calibration | Run calibration before monitoring. |
| Unexpected exception in capture thread | Structured JSON log in `%APPDATA%\SpareMyEyes\logs`; the thread restarts; the app keeps running. |
| Corrupt settings file | Log the offending content and fall back to defaults; do not overwrite the file. |

## 7. Testing

Single command: `uv run pytest`. Runs locally and in CI.

### Development process: TDD

All production code is written test-first, following red → green → refactor:

1. Write a failing test for the next behavior and run it to see it fail for the expected
   reason.
2. Write the minimum code to make it pass.
3. Refactor with the suite green.

This applies at every level:

- Analyzers, `Coach` and `BreakSession` start from unit tests.
- Each behavior in section 5 starts as a failing pipeline integration scenario, which then
  drives the unit tests and code beneath it.
- Adapters (`OpenCvFrameSource`, `MediaPipeFaceLandmarker`, `TkNotifier`) start from their
  integration or smoke tests.
- Every bug fix starts with a regression test that reproduces it.

No production code is merged without a test that failed before it existed.

### Test levels

1. **Unit tests** — each analyzer, `Coach` and `BreakSession` fed with sample sequences:
   complete, incomplete and deliberate blinks; distance crossing thresholds with hysteresis;
   gaze toward and away from the window; presence transitions.
2. **Pipeline integration tests (no camera)** — `ScriptedFaceSampleSource` replays a
   timeline (e.g. 3 minutes at 5 blinks/min, then normal) through the real analyzers and the
   real `Coach`, with `FakeClock` and `RecordingNotifier`. Covered scenarios:
   - nudge shows, hides after 2 complete blinks, respects cooldown;
   - incomplete-blink wording;
   - distance alert with hysteresis and cooldown;
   - full break: gaze 20 s + 5 slow blinks; snooze; skip; timeout;
   - absence pausing and resetting the screen-time counter;
   - camera failure and camera busy with fallback to idle-time reminders.
3. **MediaPipe integration tests** — the real Face Landmarker on still images (eyes open,
   eyes closed, head turned left and right, face near and far). Assert EAR, yaw and iris size
   fall within expected ranges. Images are public domain or CC0, with source and license
   recorded in `tests/fixtures/CREDITS.md`.
4. **App smoke test** — start the full app with `--scripted-camera <scenario>`, run a few
   seconds, assert the tray and overlays were created and the app exits cleanly.
5. **Manual checklist** — `docs/manual-test-checklist.md` for real-webcam checks
   (calibration, lighting, glasses, CPU use).

Test names follow `method_scenario_expected_result`.

## 8. Repository layout

```
spare-my-eyes/
├─ pyproject.toml
├─ README.md
├─ LICENSE
├─ src/spare_my_eyes/
│  ├─ capture/
│  ├─ analysis/
│  ├─ coaching/
│  ├─ ui/
│  ├─ calibration.py
│  ├─ settings.py
│  ├─ clock.py
│  └─ app.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
├─ docs/
└─ .github/workflows/
```

Tooling: uv, pytest, ruff (format + lint), mypy strict.

## 9. Delivery

- **CI** (GitHub Actions, `windows-latest`): ruff, mypy and the full test suite on every push
  and pull request. Free for public repositories.
- **Release**: pushing a `v*` tag builds a PyInstaller one-folder app and attaches two assets
  to the GitHub Release: an Inno Setup installer (`SpareMyEyes-Setup-<version>.exe`) and a
  portable zip.
- **Installer**: per-user install (no admin rights) under `%LOCALAPPDATA%\Programs`, Start menu
  shortcut, optional desktop shortcut, optional "start when I sign in" (the same Run registry
  value the settings window toggles), "launch now" at the end, and an uninstaller that stops
  the app and removes the Run value. User data in `%APPDATA%\SpareMyEyes` is kept. The
  installer is not code-signed, so SmartScreen shows "unknown publisher" (a signing
  certificate costs about US$100+/year and is out of scope).
- The MediaPipe `face_landmarker.task` model (~4 MB, Apache 2.0) is downloaded during build
  and verified by SHA-256.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Blink completeness misclassified at 20 fps | Treat as an estimate; rely on rate for the main nudge; tune with the manual checklist. |
| Webcam focal length varies | Distance calibration at arm's length. |
| Some webcams are exclusive and block meeting apps | Release the camera on read failure; document the limitation. |
| CPU use higher than expected | Configurable fps; measure in the manual checklist. |
| No suitable CC0 face images for every pose | Document the gap and mark the missing cases; never commit the author's face. |

## 11. References

- Aston University — The effects of breaks on digital eye strain, dry eye and binocular
  vision: testing the 20-20-20 rule. https://www.sciencedirect.com/science/article/pii/S1367048422001990
- Review of Optometry — 20/20/20 still not enough to alleviate eye strain.
  https://www.reviewofoptometry.com/news/article/202020-still-not-enough-to-alleviate-eye-strain
- A smartphone-based blink training application for alleviating dry eye signs and symptoms.
  https://www.epistemonikos.org/en/documents/5bc5458d432e546d11a1b2350d4e29c738a3ba6e
- American Optometric Association — The benefits of blinking.
  https://aoa.org/news/clinical-eye-care/the-benefits-of-blinking
- From the ocular surface to neurophysiology: an integrative review of digital eye strain.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12967517/
- Real-time blink detection as an indicator of computer vision syndrome in real-life settings.
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10001854/
- American Academy of Ophthalmology — Computers, digital devices, and eye strain.
  https://www.aao.org/eye-health/tips-prevention/computer-usage
