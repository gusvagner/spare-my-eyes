import pytest

from spare_my_eyes.coaching.break_session import (
    BreakOutcome,
    BreakSession,
    BreakStep,
    BreakTargets,
)

FPS = 20.0
TARGETS = BreakTargets()


def observe_for(
    session: BreakSession, start: float, end: float, looking: bool, ear_ratio: float = 1.0
) -> None:
    for index in range(round((end - start) * FPS) + 1):
        session.observe(start + index / FPS, looking, ear_ratio)


def close_eyes(session: BreakSession, start: float, closed_seconds: float) -> None:
    for index in range(round(closed_seconds * FPS)):
        session.observe(start + index / FPS, False, 0.2)
    session.observe(start + closed_seconds, False, 1.0)


def session_on_blink_step() -> BreakSession:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 20.0, looking=True)
    return session


def test_progress_new_session_starts_looking_out() -> None:
    progress = BreakSession.verified_by_camera(0.0, TARGETS).progress()
    assert progress.step is BreakStep.LOOK_OUT
    assert progress.gaze_seconds == 0.0
    assert progress.verified


def test_observe_looking_at_window_for_target_moves_to_slow_blinks() -> None:
    progress = session_on_blink_step().progress()
    assert progress.step is BreakStep.SLOW_BLINKS
    assert progress.gaze_seconds == pytest.approx(20.0)


def test_observe_looking_away_does_not_advance_gaze() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 30.0, looking=False)
    assert session.progress().gaze_seconds == 0.0
    assert session.progress().step is BreakStep.LOOK_OUT


def test_observe_gaze_accumulates_across_interruptions() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 10.0, looking=True)
    observe_for(session, 10.05, 15.0, looking=False)
    observe_for(session, 15.05, 25.0, looking=True)
    assert session.progress().step is BreakStep.SLOW_BLINKS


def test_observe_five_slow_blinks_completes_break() -> None:
    session = session_on_blink_step()
    for index in range(5):
        close_eyes(session, 21.0 + index * 2.0, closed_seconds=0.4)
    assert session.outcome is BreakOutcome.COMPLETED


def test_observe_quick_blinks_do_not_count() -> None:
    session = session_on_blink_step()
    for index in range(5):
        close_eyes(session, 21.0 + index * 2.0, closed_seconds=0.15)
    assert session.progress().slow_blinks == 0
    assert session.outcome is None


def test_check_timeout_two_minutes_without_progress_times_out() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 120.0, looking=False)
    session.check_timeout(120.0)
    assert session.outcome is BreakOutcome.TIMED_OUT


def test_check_timeout_recent_progress_keeps_session_open() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    observe_for(session, 0.0, 10.0, looking=True)
    session.check_timeout(125.0)
    assert session.outcome is None


def test_skip_open_session_records_skipped() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    session.skip()
    assert session.outcome is BreakOutcome.SKIPPED


def test_observe_after_outcome_is_ignored() -> None:
    session = BreakSession.verified_by_camera(0.0, TARGETS)
    session.skip()
    observe_for(session, 0.0, 20.0, looking=True)
    assert session.progress().gaze_seconds == 0.0


def test_advance_unverified_idle_user_progresses_by_time_and_completes() -> None:
    session = BreakSession.on_honor_system(0.0, TARGETS)
    for second in range(21):
        session.advance_unverified(float(second), user_is_idle=True)
    assert session.progress().step is BreakStep.SLOW_BLINKS
    assert not session.progress().verified
    for second in range(21, 31):
        session.advance_unverified(float(second), user_is_idle=True)
    assert session.outcome is BreakOutcome.COMPLETED


def test_advance_unverified_active_user_does_not_progress() -> None:
    session = BreakSession.on_honor_system(0.0, TARGETS)
    for second in range(30):
        session.advance_unverified(float(second), user_is_idle=False)
    assert session.progress().gaze_seconds == 0.0
