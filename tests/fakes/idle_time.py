class FakeIdleTimeProvider:
    def __init__(self, seconds: float = 0.0) -> None:
        self.seconds = seconds

    def idle_seconds(self) -> float:
        return self.seconds
