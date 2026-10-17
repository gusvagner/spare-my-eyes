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
