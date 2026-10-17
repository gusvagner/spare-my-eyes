import pytest

from tests.fakes.logs import RecordingLogHandler


@pytest.fixture
def log_recorder(request: pytest.FixtureRequest) -> RecordingLogHandler:
    return RecordingLogHandler.attached_to_new_logger(request.node.name)
