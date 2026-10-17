from collections.abc import Iterable

import pytest

from spare_my_eyes.analysis.blink_detector import Blink, BlinkDetector, BlinkKind
from spare_my_eyes.capture.camera_errors import CameraUnavailableError
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.capture.sample_source import UnavailableSampleSource
from spare_my_eyes.capture.scenarios import SCENARIOS
from spare_my_eyes.capture.scripted import (
    OPEN_EAR,
    ScriptedBlink,
    ScriptedFaceSampleSource,
    TimelineSegment,
    generate_samples,
)
from tests.fakes.clock import FakeClock
from tests.fakes.sleeper import RecordingSleeper


def detected_blinks(samples: Iterable[FaceSample]) -> list[Blink]:
    detector = BlinkDetector(OPEN_EAR)
    return [blink for sample in samples if (blink := detector.update(sample)) is not None]


def scripted_source(duration: float, sleeper: RecordingSleeper) -> ScriptedFaceSampleSource:
    return ScriptedFaceSampleSource([TimelineSegment(duration)], 20.0, FakeClock(100.0), sleeper)


def test_generate_samples_one_second_segment_produces_frames_at_fps() -> None:
    samples = list(generate_samples([TimelineSegment(1.0)], fps=20.0))
    assert len(samples) == 20
    assert samples[-1].timestamp == pytest.approx(0.95)


def test_generate_samples_blink_rate_produces_matching_blink_count() -> None:
    blinks = detected_blinks(generate_samples([TimelineSegment(60.0, blinks_per_minute=12.0)]))
    assert len(blinks) == 12
    assert {blink.kind for blink in blinks} == {BlinkKind.COMPLETE}


def test_generate_samples_incomplete_blinks_are_classified_incomplete() -> None:
    segment = TimelineSegment(30.0, blinks_per_minute=12.0, blink=ScriptedBlink.INCOMPLETE)
    blinks = detected_blinks(generate_samples([segment]))
    assert {blink.kind for blink in blinks} == {BlinkKind.INCOMPLETE}


def test_generate_samples_slow_blinks_last_between_300_and_500_ms() -> None:
    segment = TimelineSegment(10.0, blinks_per_minute=30.0, blink=ScriptedBlink.SLOW)
    blinks = detected_blinks(generate_samples([segment]))
    assert len(blinks) == 5
    assert all(0.3 <= blink.duration_seconds <= 0.5 for blink in blinks)


def test_generate_samples_zero_blink_rate_keeps_eyes_open() -> None:
    samples = generate_samples([TimelineSegment(5.0, blinks_per_minute=0.0)])
    assert {sample.mean_ear for sample in samples} == {OPEN_EAR}


def test_generate_samples_absent_segment_has_no_face() -> None:
    samples = generate_samples([TimelineSegment(1.0, face_present=False)])
    assert not any(sample.face_present for sample in samples)


def test_generate_samples_consecutive_segments_continue_timestamps() -> None:
    samples = list(generate_samples([TimelineSegment(1.0), TimelineSegment(1.0)], start=10.0))
    assert samples[20].timestamp == pytest.approx(11.0)
    assert samples[-1].timestamp == pytest.approx(11.95)


def test_next_sample_scripted_source_paces_and_stamps_with_clock() -> None:
    sleeper = RecordingSleeper()
    source = scripted_source(1.0, sleeper)
    source.open()
    assert source.next_sample().timestamp == 100.0
    assert sleeper.calls == [pytest.approx(0.05)]


def test_next_sample_scripted_source_loops_after_timeline_ends() -> None:
    source = scripted_source(0.1, RecordingSleeper())
    source.open()
    samples = [source.next_sample() for _ in range(5)]
    assert all(sample.face_present for sample in samples)


def test_next_sample_before_open_raises_camera_unavailable() -> None:
    with pytest.raises(CameraUnavailableError):
        scripted_source(1.0, RecordingSleeper()).next_sample()


def test_open_unavailable_source_raises_with_reason() -> None:
    with pytest.raises(CameraUnavailableError, match="model missing"):
        UnavailableSampleSource("model missing at C:/x.task").open()


def test_scenarios_every_name_has_segments() -> None:
    assert set(SCENARIOS) == {"normal", "low-blink-rate", "incomplete-blinks", "too-close", "away"}
    assert all(SCENARIOS.values())
