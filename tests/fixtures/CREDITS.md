# Test fixture credits

Every image here is public domain or CC0. Each row links to the file page that states the license.

| File | Source | Author | License |
|---|---|---|---|

Derived cases generated in code, no extra files:
- head turned right = horizontal flip of `head_turned_left.jpg`
- face far away = `frontal_eyes_open.jpg` shrunk to half size on a gray canvas
- no face = a plain gray frame

## Missing cases

These images are not committed yet. The tests that need them are skipped with a message that
points to this file. To add one, find a CC0 or public-domain photo on Wikimedia Commons
(https://commons.wikimedia.org, use the license filter and confirm on the file page), scale it
to about 640 px wide, save it under `tests/fixtures/faces/`, and add a row to the table above.
Never use the author's own face.

| File | Content needed |
|---|---|
| `faces/frontal_eyes_open.jpg` | One adult face, frontal, eyes open, face at least 200 px wide |
| `faces/frontal_eyes_closed.jpg` | One adult face, frontal, eyes fully closed |
| `faces/head_turned_left.jpg` | One face turned ~30–45° to the subject's own left (nose toward the right edge of the image) |
