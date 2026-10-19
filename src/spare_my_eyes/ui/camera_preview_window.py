import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from PIL import ImageTk

from spare_my_eyes.capture.camera_preview_feed import CameraPreviewFeed, PreviewSnapshot
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.factory import build_live_readout
from spare_my_eyes.settings import Settings
from spare_my_eyes.ui.preview_image import render_preview
from spare_my_eyes.ui.preview_text import WAITING_FOR_CAMERA, describe_reading


class CameraPreviewWindow:
    """Shows what the camera sees and what the app measures, so the user can check detection."""

    TITLE = "Spare My Eyes camera"
    REFRESH_MS = 66
    STALE_AFTER_SECONDS = 2.0
    IMAGE_WIDTH = 480

    def __init__(
        self, root: tk.Tk, feed: CameraPreviewFeed, settings: Settings, clock: Clock
    ) -> None:
        self._feed = feed
        self._settings = settings
        self._clock = clock
        self._open = True
        self._photo: ImageTk.PhotoImage | None = None
        feed.start(build_live_readout(settings))
        self.window = tk.Toplevel(root)
        self.window.title(self.TITLE)
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._build_labels()
        self.window.after(self.REFRESH_MS, self._refresh_repeatedly)

    @property
    def is_open(self) -> bool:
        return self._open

    def refresh(self) -> None:
        snapshot = self._feed.latest()
        if snapshot is None or self._is_stale(snapshot):
            self.readout_label.configure(text=WAITING_FOR_CAMERA)
            return
        self._photo = ImageTk.PhotoImage(
            render_preview(snapshot, self.IMAGE_WIDTH), master=self.window
        )
        self.image_label.configure(image=self._photo)
        lines = describe_reading(snapshot.reading, self._settings.window_side)
        self.readout_label.configure(text="\n".join(lines))

    def close(self) -> None:
        self._open = False
        self._feed.stop()
        self.window.destroy()

    def bring_to_front(self) -> None:
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def _build_labels(self) -> None:
        frame = ttk.Frame(self.window, padding=12)
        frame.pack(fill="both")
        self.image_label = ttk.Label(frame)
        self.image_label.pack()
        self.readout_label = ttk.Label(frame, justify="left", wraplength=self.IMAGE_WIDTH)
        self.readout_label.pack(anchor="w", pady=(8, 0))

    def _is_stale(self, snapshot: PreviewSnapshot) -> bool:
        return self._clock.now() - snapshot.captured_at > self.STALE_AFTER_SECONDS

    def _refresh_repeatedly(self) -> None:
        if not self._open:
            return
        self.refresh()
        self.window.after(self.REFRESH_MS, self._refresh_repeatedly)


class CameraPreviewOpener:
    def __init__(
        self,
        root: tk.Tk,
        feed: CameraPreviewFeed,
        current_settings: Callable[[], Settings],
        clock: Clock,
    ) -> None:
        self._root = root
        self.feed = feed
        self._current_settings = current_settings
        self._clock = clock
        self._window: CameraPreviewWindow | None = None

    @property
    def current(self) -> CameraPreviewWindow | None:
        return self._window

    def __call__(self) -> None:
        if self._window is not None and self._window.is_open:
            self._window.bring_to_front()
            return
        settings = self._current_settings()
        self._window = CameraPreviewWindow(self._root, self.feed, settings, self._clock)
