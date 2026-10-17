from collections.abc import Iterable

import pytest

from spare_my_eyes.analysis.blink_detector import Blink, BlinkDetector, BlinkKind
from spare_my_eyes.capture.face_sample import FaceSample
from tests.fakes.samples import blink_of, samples_from_ears

BASELINE = 0.30


def detect_all(detector: BlinkDetector, samples: Iterable[FaceSample]) -> list[Blink]:
    return [blink for sample in samples if (blink := detector.update(sample)) is not None]


def test_update_short_deep_closure_reports_complete_blink() -> None:
    blinks = detect_all(BlinkDetector(BASELINE), samples_from_ears([0.30, 0.18, 0.06, 0.18, 0.30]))
    assert len(blinks) == 1
    assert blinks[0].kind is BlinkKind.COMPLETE
    assert blinks[0].duration_seconds == pytest.approx(0.15)
    assert blinks[0].min_ear_ratio == pytest.approx(0.2)
    assert blinks[0].ended_at == pytest.approx(0.2)


def test_update_short_shallow_closure_reports_incomplete_blink() -> None:
    blinks = detect_all(BlinkDetector(BASELINE), samples_from_ears([0.30, 0.20, 0.15, 0.20, 0.30]))
    assert [blink.kind for blink in blinks] == [BlinkKind.INCOMPLETE]


def test_update_closure_longer_than_half_second_reports_deliberate_closure() -> None:
    ears = [0.30] + [0.05] * 12 + [0.30]
    blinks = detect_all(BlinkDetector(BASELINE), samples_from_ears(ears))
    assert [blink.kind for blink in blinks] == [BlinkKind.DELIBERATE]


def test_update_eyes_open_reports_nothing() -> None:
    assert detect_all(BlinkDetector(BASELINE), samples_from_ears([0.30] * 40)) == []


def test_update_face_lost_mid_blink_discards_blink() -> None:
    samples = [
        *samples_from_ears([0.30, 0.06]),
        FaceSample.absent(0.10),
        *samples_from_ears([0.30], start=0.15),
    ]
    assert detect_all(BlinkDetector(BASELINE), samples) == []


def test_reset_mid_blink_discards_blink() -> None:
    detector = BlinkDetector(BASELINE)
    detect_all(detector, samples_from_ears([0.30, 0.06]))
    detector.reset()
    assert detect_all(detector, samples_from_ears([0.30], start=0.10)) == []


def test_init_non_positive_baseline_raises_value_error() -> None:
    with pytest.raises(ValueError, match="open_ear_baseline"):
        BlinkDetector(0.0)


def test_is_spontaneous_deliberate_closure_returns_false() -> None:
    assert blink_of(BlinkKind.COMPLETE).is_spontaneous
    assert not blink_of(BlinkKind.DELIBERATE).is_spontaneous
