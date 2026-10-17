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
