from spare_my_eyes.coaching.controller import EyeCareController
from spare_my_eyes.settings_form import (
    SettingsFormError,
    SettingsFormInput,
    apply_form,
    form_input_from,
    parse_form,
)
from spare_my_eyes.system.startup_registration import StartupRegistration


class SettingsEditor:
    """Turns a submitted settings form into saved settings, live coaching and a startup entry."""

    def __init__(self, controller: EyeCareController, startup: StartupRegistration) -> None:
        self._controller = controller
        self._startup = startup

    @property
    def startup_available(self) -> bool:
        return self._startup.is_available

    def current_form(self) -> SettingsFormInput:
        enabled = self._startup.is_available and self._startup.is_enabled()
        return form_input_from(self._controller.settings, enabled)

    def submit(self, form: SettingsFormInput) -> list[str]:
        try:
            values = parse_form(form)
        except SettingsFormError as error:
            return error.problems
        self._controller.apply_settings(apply_form(self._controller.settings, values))
        self._apply_startup(values.start_with_windows)
        return []

    def _apply_startup(self, wanted: bool) -> None:
        if not self._startup.is_available:
            return
        if wanted:
            self._startup.enable()
        else:
            self._startup.disable()
