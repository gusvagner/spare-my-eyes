from enum import StrEnum
from typing import Protocol

from spare_my_eyes.capture.camera_errors import CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample


class CameraStatus(StrEnum):
    ACTIVE = "active"
    UNAVAILABLE = "unavailable"
    BUSY = "busy"


class FaceSampleSource(Protocol):
    def open(self) -> None: ...

    def next_sample(self) -> FaceSample: ...

    def close(self) -> None: ...


class UnavailableSampleSource:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def open(self) -> None:
        raise CameraUnavailableError(self._reason)

    def next_sample(self) -> FaceSample:
        raise CameraUnavailableError(self._reason)

    def close(self) -> None:
        return None
