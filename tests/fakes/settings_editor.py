from spare_my_eyes.settings_form import SettingsFormInput


class FakeSettingsEditor:
    def __init__(
        self,
        form: SettingsFormInput,
        problems: list[str] | None = None,
        startup_available: bool = True,
    ) -> None:
        self.form = form
        self.problems = problems if problems is not None else []
        self.submitted: list[SettingsFormInput] = []
        self._startup_available = startup_available

    @property
    def startup_available(self) -> bool:
        return self._startup_available

    def current_form(self) -> SettingsFormInput:
        return self.form

    def submit(self, form: SettingsFormInput) -> list[str]:
        self.submitted.append(form)
        return self.problems
