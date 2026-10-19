from pathlib import Path

from spare_my_eyes.capture.camera_preview_feed import CameraPreviewFeed
from spare_my_eyes.capture.sample_source import UnavailableSampleSource
from spare_my_eyes.capture.scripted import ScriptedFaceSampleSource
from spare_my_eyes.capture.source_factory import build_sample_source
from spare_my_eyes.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.logs import RecordingLogHandler


def test_build_sample_source_scripted_name_returns_scripted_source(
    log_recorder: RecordingLogHandler,
) -> None:
    source = build_sample_source(
        "normal", Settings(), FakeClock(), CameraPreviewFeed(), log_recorder.logger
    )
    assert isinstance(source, ScriptedFaceSampleSource)


def test_build_sample_source_missing_model_returns_unavailable_source(
    tmp_path: Path, log_recorder: RecordingLogHandler
) -> None:
    missing = tmp_path / "face_landmarker.task"
    source = build_sample_source(
        None, Settings(), FakeClock(), CameraPreviewFeed(), log_recorder.logger, missing
    )
    assert isinstance(source, UnavailableSampleSource)
    assert log_recorder.fields_of("model_missing") == {"path": str(missing)}
