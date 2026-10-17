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
