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
