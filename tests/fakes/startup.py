class FakeStartupRegistration:
    def __init__(self, available: bool = True, enabled: bool = False) -> None:
        self._available = available
        self.enabled = enabled

    @property
    def is_available(self) -> bool:
        return self._available

    def is_enabled(self) -> bool:
        return self.enabled

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False
