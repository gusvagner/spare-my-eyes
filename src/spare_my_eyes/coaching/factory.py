from spare_my_eyes.analysis.blink_detector import BlinkDetector
from spare_my_eyes.analysis.blink_rate import BlinkRateMonitor
from spare_my_eyes.analysis.distance import DistanceThresholds, ScreenDistanceEstimator
from spare_my_eyes.analysis.gaze import WindowGazeDetector
from spare_my_eyes.analysis.presence import PresenceTracker
from spare_my_eyes.clock import Clock
from spare_my_eyes.coaching.blink_nudge import BlinkNudgePolicy, BlinkNudgeRules
from spare_my_eyes.coaching.break_policy import BreakPolicy, BreakSchedule
from spare_my_eyes.coaching.break_session import BreakTargets
from spare_my_eyes.coaching.coach import Coach
from spare_my_eyes.coaching.cooldown import Cooldown
from spare_my_eyes.coaching.distance_alert import DistanceAlertPolicy
from spare_my_eyes.coaching.notifier import Notifier
from spare_my_eyes.settings import Settings
from spare_my_eyes.system.idle_time import IdleTimeProvider

DEFAULT_OPEN_EAR = 0.28
DEFAULT_FOCAL_SCALE = 660.0


def build_coach(
    settings: Settings, clock: Clock, notifier: Notifier, idle: IdleTimeProvider
) -> Coach:
    baseline = settings.open_ear_baseline or DEFAULT_OPEN_EAR
    nudge = _blink_nudge_policy(settings, baseline, notifier)
    distance = _distance_alert_policy(settings, notifier)
    breaks = _break_policy(settings, baseline, notifier, clock)
    return Coach([nudge, distance], breaks, nudge.current_rate, idle, notifier, clock)


def _blink_nudge_policy(
    settings: Settings, baseline: float, notifier: Notifier
) -> BlinkNudgePolicy:
    rules = BlinkNudgeRules(
        rate_threshold_per_minute=settings.blink_rate_threshold_per_minute,
        incomplete_ratio_threshold=settings.incomplete_ratio_threshold,
        max_visible_seconds=settings.nudge_max_seconds,
        hide_after_complete_blinks=settings.nudge_hide_after_complete_blinks,
        cooldown_seconds=settings.nudge_cooldown_seconds,
    )
    monitor = BlinkRateMonitor(settings.blink_window_seconds)
    return BlinkNudgePolicy(BlinkDetector(baseline), monitor, rules, notifier)


def _distance_alert_policy(settings: Settings, notifier: Notifier) -> DistanceAlertPolicy:
    thresholds = DistanceThresholds(
        too_close_cm=settings.too_close_cm,
        clear_cm=settings.distance_clear_cm,
        hold_seconds=settings.distance_hold_seconds,
    )
    focal_scale = settings.focal_scale or DEFAULT_FOCAL_SCALE
    estimator = ScreenDistanceEstimator(focal_scale, thresholds)
    return DistanceAlertPolicy(estimator, Cooldown(settings.distance_cooldown_seconds), notifier)


def _break_policy(
    settings: Settings, baseline: float, notifier: Notifier, clock: Clock
) -> BreakPolicy:
    schedule = BreakSchedule(
        interval_seconds=settings.break_interval_seconds,
        snooze_seconds=settings.snooze_seconds,
        absence_reset_seconds=settings.absence_reset_seconds,
    )
    targets = BreakTargets(
        gaze_seconds=settings.break_gaze_seconds,
        slow_blinks=settings.break_slow_blinks,
        slow_blink_min_seconds=settings.slow_blink_min_seconds,
        inactivity_timeout_seconds=settings.break_inactivity_timeout_seconds,
    )
    gaze = WindowGazeDetector(settings.window_side, settings.break_min_yaw_degrees)
    presence = PresenceTracker(settings.absent_after_seconds)
    return BreakPolicy(schedule, targets, gaze, presence, baseline, notifier, clock)
