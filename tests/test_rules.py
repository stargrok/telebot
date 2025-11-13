from telebot.rules import ActionType, RuleEngine


def test_banned_keyword_deletes_message():
    config = {"banned_keywords": ["spam"]}
    engine = RuleEngine.from_config(config)
    matches = engine.match("this spam message should be deleted")
    assert matches
    assert matches[0].action.type is ActionType.DELETE


def test_auto_reply_can_mark_delete_original():
    config = {"auto_replies": [{"keyword": "test", "reply": "ok", "delete_original": True}]}
    engine = RuleEngine.from_config(config)
    match = engine.match("test content")[0]
    assert match.rule.delete_original is True


def test_auto_reply_and_points_can_trigger_together():
    config = {
        "auto_replies": [{"keyword": "hello", "reply": "hi", "delete_original": False}],
        "point_rules": [{"regex": r"hello", "points": 2}],
    }
    engine = RuleEngine.from_config(config)
    matches = engine.match("hello telebot")
    assert len(matches) == 2
    action_types = {match.action.type for match in matches}
    assert ActionType.REPLY in action_types
    assert ActionType.ADD_POINTS in action_types
