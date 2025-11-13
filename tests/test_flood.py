from telebot.flood import FloodProtector
from telebot.rules import ActionType


def test_flood_protector_triggers_and_resets():
    protector = FloodProtector()
    config = {
        "enabled": True,
        "max_messages": 2,
        "interval_seconds": 10,
        "mute_seconds": 30,
        "notice": "slow down",
    }
    assert protector.check(1, 1, config, now=0) is None
    assert protector.check(1, 1, config, now=1) is None
    action = protector.check(1, 1, config, now=2)
    assert action is not None
    assert action.type is ActionType.MUTE
    assert action.duration == 30
    assert action.message == "slow down"
    assert protector.check(1, 1, config, now=3) is None


def test_flood_protector_ignores_disabled_config():
    protector = FloodProtector()
    assert protector.check(99, 42, {"enabled": False}, now=0) is None
