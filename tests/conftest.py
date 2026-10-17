import tkinter as tk
from collections.abc import Iterator

import pytest

from tests.fakes.logs import RecordingLogHandler


@pytest.fixture
def log_recorder(request: pytest.FixtureRequest) -> RecordingLogHandler:
    return RecordingLogHandler.attached_to_new_logger(request.node.name)


@pytest.fixture(scope="session")
def tk_root() -> Iterator[tk.Tk]:
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()
