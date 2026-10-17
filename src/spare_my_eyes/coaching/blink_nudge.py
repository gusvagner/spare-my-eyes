from dataclasses import dataclass

from spare_my_eyes.analysis.blink_detector import Blink, BlinkDetector, BlinkKind
from spare_my_eyes.analysis.blink_rate import BlinkRateMonitor, BlinkStats
from spare_my_eyes.capture.face_sample import FaceSample
from spare_my_eyes.coaching.cooldown import Cooldown
from spare_my_eyes.coaching.notifier import Notifier

BLINK_MESSAGE = "Blink"
SLOW_BLINK_MESSAGE = "Blink slowly, close fully"


@dataclass(frozen=True, slots=True)
class BlinkNudgeRules:
    rate_threshold_per_minute: float = 8.0
    incomplete_ratio_threshold: float = 0.3
    max_visible_seconds: float = 8.0
    hide_after_complete_blinks: int = 2
    cooldown_seconds: float = 180.0


class BlinkNudgePolicy:
    def __init__(
        self,
        detector: BlinkDetector,
        monitor: BlinkRateMonitor,
        rules: BlinkNudgeRules,
        notifier: Notifier,
    ) -> None:
        self._detector = detector
        self._monitor = monitor
        self._rules = rules
        self._notifier = notifier
        self._cooldown = Cooldown(rules.cooldown_seconds)
        self._shown_at: float | None = None
        self._complete_blinks_while_shown = 0

    def on_sample(self, sample: FaceSample) -> None:
        blink = self._detector.update(sample)
        self._monitor.observe(sample)
        if blink is not None:
            self._monitor.record(blink)
            self._count_toward_hiding(blink)
        self._show_when_needed(sample.timestamp)

    def on_tick(self, now: float) -> None:
        if self._shown_at is None:
            return
        if now - self._shown_at >= self._rules.max_visible_seconds:
            self._hide(now)

    def suspend(self) -> None:
        if self._shown_at is not None:
            self._notifier.hide_blink_nudge()
        self._shown_at = None
        self._detector.reset()
        self._monitor.reset()
        self._cooldown.clear()

    def current_rate(self) -> float | None:
        stats = self._monitor.stats()
        return None if stats is None else stats.blinks_per_minute

    def _count_toward_hiding(self, blink: Blink) -> None:
        if self._shown_at is None or blink.kind is not BlinkKind.COMPLETE:
            return
        self._complete_blinks_while_shown += 1
        if self._complete_blinks_while_shown >= self._rules.hide_after_complete_blinks:
            self._hide(blink.ended_at)

    def _show_when_needed(self, now: float) -> None:
        if self._shown_at is not None or not self._cooldown.is_ready(now):
            return
        stats = self._monitor.stats()
        if stats is None or not self._is_rate_low(stats):
            return
        self._notifier.show_blink_nudge(self._message_for(stats))
        self._shown_at = now
        self._complete_blinks_while_shown = 0

    def _is_rate_low(self, stats: BlinkStats) -> bool:
        return stats.window_full and stats.blinks_per_minute < self._rules.rate_threshold_per_minute

    def _message_for(self, stats: BlinkStats) -> str:
        if stats.incomplete_ratio > self._rules.incomplete_ratio_threshold:
            return SLOW_BLINK_MESSAGE
        return BLINK_MESSAGE

    def _hide(self, now: float) -> None:
        self._notifier.hide_blink_nudge()
        self._shown_at = None
        self._cooldown.start(now)
