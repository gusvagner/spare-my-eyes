from spare_my_eyes.capture.face_sample import FaceSample


class RecordingPolicy:
    def __init__(self) -> None:
        self.samples: list[FaceSample] = []
        self.ticks: list[float] = []
        self.suspensions = 0

    def on_sample(self, sample: FaceSample) -> None:
        self.samples.append(sample)

    def on_tick(self, now: float) -> None:
        self.ticks.append(now)

    def suspend(self) -> None:
        self.suspensions += 1


class RecordingBreakControl:
    def __init__(self) -> None:
        self.samples: list[FaceSample] = []
        self.ticks: list[tuple[float, float]] = []
        self.commands: list[str] = []
        self.camera_active = True

    def on_sample(self, sample: FaceSample) -> None:
        self.samples.append(sample)

    def on_tick(self, now: float, idle_seconds: float) -> None:
        self.ticks.append((now, idle_seconds))

    def start_now(self) -> None:
        self.commands.append("start_now")

    def snooze(self) -> None:
        self.commands.append("snooze")

    def skip(self) -> None:
        self.commands.append("skip")

    def suspend(self) -> None:
        self.commands.append("suspend")

    def use_camera(self) -> None:
        self.camera_active = True

    def use_idle_time(self) -> None:
        self.camera_active = False
