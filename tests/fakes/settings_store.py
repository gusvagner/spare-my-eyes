from spare_my_eyes.settings import Settings


class InMemorySettingsStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else Settings()
        self.saved: list[Settings] = []

    def load(self) -> Settings:
        return self.settings

    def save(self, settings: Settings) -> None:
        self.settings = settings
        self.saved.append(settings)
