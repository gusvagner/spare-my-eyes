from collections.abc import Iterable

import pytest

from spare_my_eyes.calibration import (
    CalibrationProgress,
    CalibrationResult,
    CalibrationSession,
    CalibrationStep,
)
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import samples_from_ears


def feed(session: CalibrationSession, samples: Iterable[FaceSample]) -> CalibrationProgress:
    progress = session.progress(0.0)
    for sample in samples:
        progress = session.update(sample)
    return progress


def test_update_twenty_seconds_of_face_produces_result() -> None:
    session = CalibrationSession(started_at=0.0)
    progress = feed(session, samples_from_ears([0.30] * 401, iris_diameter_px=11.0))
    assert progress.step is CalibrationStep.DONE
    assert session.result == CalibrationResult(open_ear_baseline=0.30, focal_scale=660.0)


def test_update_blinks_during_first_step_do_not_move_baseline() -> None:
    session = CalibrationSession(started_at=0.0)
    ears = ([0.30] * 9 + [0.05]) * 40 + [0.30]
    feed(session, samples_from_ears(ears))
    assert session.result is not None
    assert session.result.open_ear_baseline == pytest.approx(0.30)


def test_update_after_first_step_reports_arm_length_step() -> None:
    session = CalibrationSession(started_at=0.0)
    progress = feed(session, samples_from_ears([0.30] * 202))
    assert progress.step is CalibrationStep.ARM_LENGTH


def test_update_without_face_restarts_step() -> None:
    session = CalibrationSession(started_at=0.0)
    feed(session, [FaceSample.absent(index / 20.0) for index in range(201)])
    progress = feed(session, samples_from_ears([0.30] * 199, start=10.05))
    assert progress.step is CalibrationStep.LOOK_AT_SCREEN
    assert session.result is None


def test_progress_mid_step_reports_seconds_left() -> None:
    session = CalibrationSession(started_at=0.0)
    progress = feed(session, samples_from_ears([0.30] * 81))
    assert progress.step is CalibrationStep.LOOK_AT_SCREEN
    assert progress.seconds_left == pytest.approx(6.0)
