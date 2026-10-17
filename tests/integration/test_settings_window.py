import tkinter as tk
from collections.abc import Iterator

import pytest

from spare_my_eyes.settings_form import SettingsFormInput
from spare_my_eyes.ui.settings_window import SettingsWindow, SettingsWindowOpener
from tests.fakes.settings_editor import FakeSettingsEditor

pytestmark = pytest.mark.gui

FORM = SettingsFormInput("left", "20", "8", "50", "0", False)


@pytest.fixture
def opened_files() -> list[str]:
    return []


@pytest.fixture
def make_opener(tk_root: tk.Tk, opened_files: list[str]) -> Iterator[list[SettingsWindowOpener]]:
    openers: list[SettingsWindowOpener] = []
    yield openers
    for opener in openers:
        if opener.current is not None and opener.current.is_open:
            opener.current.close()


def open_window(
    tk_root: tk.Tk,
    openers: list[SettingsWindowOpener],
    editor: FakeSettingsEditor,
    opened: list[str],
) -> SettingsWindow:
    opener = SettingsWindowOpener(tk_root, editor, lambda: opened.append("file"))
    openers.append(opener)
    opener()
    assert opener.current is not None
    return opener.current


def test_opener_first_call_shows_current_values(
    tk_root: tk.Tk, make_opener: list[SettingsWindowOpener]
) -> None:
    window = open_window(tk_root, make_opener, FakeSettingsEditor(FORM), [])
    assert window.is_open
    assert window.break_interval.get() == "20"
    assert window.window_side.get() == "left"


def test_opener_second_call_reuses_open_window(
    tk_root: tk.Tk, make_opener: list[SettingsWindowOpener]
) -> None:
    first = open_window(tk_root, make_opener, FakeSettingsEditor(FORM), [])
    make_opener[0]()
    assert make_opener[0].current is first


def test_submit_valid_form_sends_edits_and_closes(
    tk_root: tk.Tk, make_opener: list[SettingsWindowOpener]
) -> None:
    editor = FakeSettingsEditor(FORM)
    window = open_window(tk_root, make_opener, editor, [])
    window.break_interval.set("30")
    window.submit()
    assert editor.submitted[-1].break_interval_minutes == "30"
    assert not window.is_open


def test_submit_with_problems_shows_them_and_stays_open(
    tk_root: tk.Tk, make_opener: list[SettingsWindowOpener]
) -> None:
    editor = FakeSettingsEditor(FORM, problems=["Camera number must be a whole number"])
    window = open_window(tk_root, make_opener, editor, [])
    window.submit()
    assert window.is_open
    assert "Camera number" in str(window.problems_label.cget("text"))


def test_close_without_saving_submits_nothing(
    tk_root: tk.Tk, make_opener: list[SettingsWindowOpener]
) -> None:
    editor = FakeSettingsEditor(FORM)
    window = open_window(tk_root, make_opener, editor, [])
    window.close()
    assert editor.submitted == []
    assert not window.is_open


def test_startup_unavailable_disables_checkbox(
    tk_root: tk.Tk, make_opener: list[SettingsWindowOpener]
) -> None:
    editor = FakeSettingsEditor(FORM, startup_available=False)
    window = open_window(tk_root, make_opener, editor, [])
    assert "disabled" in window.startup_checkbox.state()


def test_open_file_button_opens_settings_file(
    tk_root: tk.Tk, make_opener: list[SettingsWindowOpener], opened_files: list[str]
) -> None:
    window = open_window(tk_root, make_opener, FakeSettingsEditor(FORM), opened_files)
    window.open_file_button.invoke()
    assert opened_files == ["file"]
