import logging
from pathlib import Path

from spare_my_eyes.capture.camera_preview_feed import CameraPreviewFeed
from spare_my_eyes.capture.camera_sample_source import CameraFaceSampleSource
from spare_my_eyes.capture.mediapipe_landmarker import MediaPipeFaceLandmarker
from spare_my_eyes.capture.opencv_frame_source import OpenCvFrameSource
from spare_my_eyes.capture.sample_source import FaceSampleSource, UnavailableSampleSource
from spare_my_eyes.capture.scenarios import SCENARIOS
from spare_my_eyes.capture.scripted import ScriptedFaceSampleSource
from spare_my_eyes.clock import Clock
from spare_my_eyes.model_asset import MODEL_PATH
from spare_my_eyes.settings import Settings
from spare_my_eyes.structured_log import log_event


def build_sample_source(
    scripted_camera: str | None,
    settings: Settings,
    clock: Clock,
    preview: CameraPreviewFeed,
    logger: logging.Logger,
    model_path: Path = MODEL_PATH,
) -> FaceSampleSource:
    if scripted_camera is not None:
        return _scripted_source(scripted_camera, settings, clock)
    if not model_path.is_file():
        log_event(logger, logging.ERROR, "model_missing", path=str(model_path))
        return UnavailableSampleSource(
            f"Face landmarker model missing at {model_path}; "
            "run `uv run python -m spare_my_eyes.model_asset`"
        )
    frames = OpenCvFrameSource(settings.camera_index, fps=settings.frames_per_second)
    return CameraFaceSampleSource(frames, MediaPipeFaceLandmarker(model_path), clock, preview)


def _scripted_source(name: str, settings: Settings, clock: Clock) -> ScriptedFaceSampleSource:
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scripted camera {name!r}; expected one of {sorted(SCENARIOS)}")
    return ScriptedFaceSampleSource(SCENARIOS[name], settings.frames_per_second, clock)
