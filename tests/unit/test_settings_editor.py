from dataclasses import dataclass, replace
from functools import partial

import pytest

from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.coaching.factory import build_coach
from spare_my_eyes.settings_editor import SettingsEditor
from spare_my_eyes.settings_form import SettingsFormInput
from tests.fakes.clock import FakeClock
from tests.fakes.idle_time import FakeIdleTimeProvider
from tests.fakes.logs import RecordingLogHandler
from tests.fakes.notifier import RecordingNotifier
from tests.fakes.settings_store import InMemorySettingsStore
from tests.fakes.startup import FakeStartupRegistration
from tests.integration.pipeline_run import CALIBRATED_SETTINGS

FORM = SettingsFormInput("right", "30", "8", "50", "0", True)


@dataclass
class EditorRig:
    editor: SettingsEditor
    controller: EyeCareController
    store: InMemorySettingsStore
    startup: FakeStartupRegistration


def make_rig(log: RecordingLogHandler, startup: FakeStartupRegistration) -> EditorRig:
    clock, notifier = FakeClock(), RecordingNotifier()
    store = InMemorySettingsStore(CALIBRATED_SETTINGS)
    factory = partial(build_coach, clock=clock, notifier=notifier, idle=FakeIdleTimeProvider())
    controller = EyeCareController(CALIBRATED_SETTINGS, store, factory, notifier, clock, log.logger)
    return EditorRig(SettingsEditor(controller, startup), controller, store, startup)


@pytest.fixture
def rig(log_recorder: RecordingLogHandler) -> EditorRig:
    return make_rig(log_recorder, FakeStartupRegistration())


def test_current_form_reflects_settings_and_startup(rig: EditorRig) -> None:
    rig.startup.enabled = True
    form = rig.editor.current_form()
    assert form.break_interval_minutes == "20"
    assert form.start_with_windows


def test_submit_valid_form_applies_settings_and_enables_startup(rig: EditorRig) -> None:
    assert rig.editor.submit(FORM) == []
    assert rig.controller.settings.break_interval_seconds == 1800.0
    assert rig.store.saved[-1].window_side == "right"
    assert rig.startup.enabled


def test_submit_unchecked_startup_disables_it(rig: EditorRig) -> None:
    rig.startup.enabled = True
    rig.editor.submit(replace(FORM, start_with_windows=False))
    assert not rig.startup.enabled


def test_submit_invalid_form_returns_problems_and_saves_nothing(rig: EditorRig) -> None:
    problems = rig.editor.submit(replace(FORM, blink_threshold="0"))
    assert len(problems) == 1
    assert rig.store.saved == []


def test_submit_startup_unavailable_leaves_registry_alone(
    log_recorder: RecordingLogHandler,
) -> None:
    rig = make_rig(log_recorder, FakeStartupRegistration(available=False))
    assert rig.editor.submit(FORM) == []
    assert not rig.startup.enabled
