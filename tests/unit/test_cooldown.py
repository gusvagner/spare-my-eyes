from spare_my_eyes.coaching.cooldown import Cooldown


def test_is_ready_never_started_returns_true() -> None:
    assert Cooldown(180.0).is_ready(0.0)


def test_is_ready_within_cooldown_returns_false() -> None:
    cooldown = Cooldown(180.0)
    cooldown.start(10.0)
    assert not cooldown.is_ready(189.9)


def test_is_ready_after_cooldown_returns_true() -> None:
    cooldown = Cooldown(180.0)
    cooldown.start(10.0)
    assert cooldown.is_ready(190.0)


def test_clear_running_cooldown_makes_it_ready() -> None:
    cooldown = Cooldown(180.0)
    cooldown.start(10.0)
    cooldown.clear()
    assert cooldown.is_ready(11.0)
