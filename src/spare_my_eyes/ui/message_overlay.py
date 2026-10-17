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
