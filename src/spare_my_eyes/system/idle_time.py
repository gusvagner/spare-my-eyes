import ctypes
from typing import Protocol

_DWORD_MASK = 0xFFFFFFFF


class IdleTimeProvider(Protocol):
    def idle_seconds(self) -> float: ...


class _LastInputInfo(ctypes.Structure):
    _fields_ = (("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint))


class WindowsIdleTimeProvider:
    def idle_seconds(self) -> float:
        info = _LastInputInfo()
        info.cbSize = ctypes.sizeof(_LastInputInfo)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            raise OSError(
                f"GetLastInputInfo failed with error {ctypes.GetLastError()}; "
                "expected a nonzero return"
            )
        now_ms = int(ctypes.windll.kernel32.GetTickCount()) & _DWORD_MASK
        last_input_ms = int(info.dwTime) & _DWORD_MASK
        return float((now_ms - last_input_ms) & _DWORD_MASK) / 1000.0
