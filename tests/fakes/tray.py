from spare_my_eyes.coaching.notifier import TrayStatus


class FakeTray:
    def __init__(self) -> None:
        self.statuses: list[tuple[TrayStatus, float | None]] = []
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def set_status(self, status: TrayStatus, blinks_per_minute: float | None) -> None:
        self.statuses.append((status, blinks_per_minute))
