from telebot.welcome import (
    DEFAULT_TEMPLATE,
    load_welcome_policy,
    render_missing_username_notice,
    render_welcome_message,
)


def test_render_welcome_message_injects_placeholders():
    policy = load_welcome_policy({"enabled": True, "text": "Hi {mention}, welcome to {chat_title}"})
    text = render_welcome_message(policy, mention="@foo", first_name="Foo", chat_title="银河群")
    assert "@foo" in text
    assert "银河群" in text


def test_missing_username_notice_returns_none_without_template():
    policy = load_welcome_policy({"enabled": True})
    assert render_missing_username_notice(policy, first_name="Alice") is None


def test_missing_username_notice_renders_template():
    policy = load_welcome_policy(
        {
            "enabled": True,
            "require_username": True,
            "missing_username_notice": "{first_name} 请先设置用户名",
        }
    )
    notice = render_missing_username_notice(policy, first_name="Bob")
    assert notice == "Bob 请先设置用户名"


def test_default_template_used_when_text_missing():
    policy = load_welcome_policy({"enabled": True, "text": ""})
    text = render_welcome_message(policy, mention="@bar", first_name="Bar", chat_title="测群")
    assert DEFAULT_TEMPLATE.split(" ")[0] in text
