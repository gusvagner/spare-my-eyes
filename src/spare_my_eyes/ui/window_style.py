import ctypes
import tkinter as tk

_GWL_EXSTYLE = -20
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_NOACTIVATE = 0x08000000
_SW_HIDE = 0
_SW_SHOWNOACTIVATE = 4


def native_handle(window: tk.Toplevel) -> int:
    return int(ctypes.windll.user32.GetParent(window.winfo_id()))


def prepare_hidden_tool_window(window: tk.Toplevel, alpha: float) -> None:
    window.attributes("-alpha", 0.0)
    window.update_idletasks()
    user32 = ctypes.windll.user32
    handle = native_handle(window)
    style = int(user32.GetWindowLongW(handle, _GWL_EXSTYLE))
    user32.SetWindowLongW(handle, _GWL_EXSTYLE, style | _WS_EX_TOOLWINDOW | _WS_EX_NOACTIVATE)
    hide_window(window)
    window.attributes("-alpha", alpha)


def show_without_focus(window: tk.Toplevel) -> None:
    ctypes.windll.user32.ShowWindow(native_handle(window), _SW_SHOWNOACTIVATE)


def hide_window(window: tk.Toplevel) -> None:
    ctypes.windll.user32.ShowWindow(native_handle(window), _SW_HIDE)


def is_window_visible(window: tk.Toplevel) -> bool:
    return bool(ctypes.windll.user32.IsWindowVisible(native_handle(window)))


def is_foreground(window: tk.Toplevel) -> bool:
    return int(ctypes.windll.user32.GetForegroundWindow()) == native_handle(window)
