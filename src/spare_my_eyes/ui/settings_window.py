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
