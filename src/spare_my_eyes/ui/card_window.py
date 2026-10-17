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
