import contextlib
import sys
import winreg
from pathlib import Path
from typing import Protocol

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "SpareMyEyes"


class StartupRegistration(Protocol):
    @property
    def is_available(self) -> bool: ...

    def is_enabled(self) -> bool: ...

    def enable(self) -> None: ...

    def disable(self) -> None: ...


def installed_executable() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable)


class WindowsStartupRegistration:
    def __init__(
        self,
        executable: Path | None,
        key_path: str = RUN_KEY_PATH,
        value_name: str = RUN_VALUE_NAME,
    ) -> None:
        self._executable = executable
        self._key_path = key_path
        self._value_name = value_name

    @property
    def is_available(self) -> bool:
        return self._executable is not None

    def is_enabled(self) -> bool:
        return self.registered_command() is not None

    def registered_command(self) -> str | None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key_path) as key:
                value, _ = winreg.QueryValueEx(key, self._value_name)
        except FileNotFoundError:
            return None
        return str(value)

    def enable(self) -> None:
        if self._executable is None:
            raise RuntimeError(
                "Start with Windows needs the installed SpareMyEyes.exe; "
                f"got executable={self._executable!r} because the app runs from source"
            )
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self._key_path) as key:
            winreg.SetValueEx(key, self._value_name, 0, winreg.REG_SZ, f'"{self._executable}"')

    def disable(self) -> None:
        with (
            contextlib.suppress(FileNotFoundError),
            winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self._key_path, 0, winreg.KEY_SET_VALUE
            ) as key,
        ):
            winreg.DeleteValue(key, self._value_name)
