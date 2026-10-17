import contextlib
import winreg
from collections.abc import Iterator
from pathlib import Path

import pytest

from spare_my_eyes.system.startup_registration import WindowsStartupRegistration

TEST_PARENT_KEY = r"Software\SpareMyEyesTests"
TEST_RUN_KEY = TEST_PARENT_KEY + r"\Run"
EXECUTABLE = Path(r"C:\Apps\Spare My Eyes\SpareMyEyes.exe")


@pytest.fixture
def registration() -> Iterator[WindowsStartupRegistration]:
    yield WindowsStartupRegistration(EXECUTABLE, key_path=TEST_RUN_KEY)
    for key in (TEST_RUN_KEY, TEST_PARENT_KEY):
        with contextlib.suppress(FileNotFoundError):
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)


def test_enable_registers_quoted_executable(registration: WindowsStartupRegistration) -> None:
    registration.enable()
    assert registration.is_enabled()
    assert registration.registered_command() == f'"{EXECUTABLE}"'


def test_disable_removes_registration(registration: WindowsStartupRegistration) -> None:
    registration.enable()
    registration.disable()
    assert not registration.is_enabled()


def test_disable_never_registered_does_nothing(registration: WindowsStartupRegistration) -> None:
    registration.disable()
    assert not registration.is_enabled()


def test_enable_running_from_source_raises_runtime_error() -> None:
    registration = WindowsStartupRegistration(None, key_path=TEST_RUN_KEY)
    assert not registration.is_available
    with pytest.raises(RuntimeError, match="installed"):
        registration.enable()
