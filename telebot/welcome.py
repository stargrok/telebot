"""Utilities for configurable welcome messages."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TEMPLATE = "欢迎 {mention} 加入 {chat_title}!"


@dataclass(slots=True)
class WelcomePolicy:
    enabled: bool = False
    text: str = DEFAULT_TEMPLATE
    require_username: bool = False
    missing_username_notice: str | None = None


def load_welcome_policy(config: dict | None) -> WelcomePolicy:
    if not config:
        return WelcomePolicy()
    return WelcomePolicy(
        enabled=config.get("enabled", False),
        text=config.get("text") or DEFAULT_TEMPLATE,
        require_username=config.get("require_username", False),
        missing_username_notice=config.get("missing_username_notice"),
    )


def render_welcome_message(policy: WelcomePolicy, *, mention: str, first_name: str, chat_title: str) -> str:
    template = policy.text or DEFAULT_TEMPLATE
    safe_first_name = first_name or mention
    safe_chat_title = chat_title or "本群"
    return template.format(mention=mention, first_name=safe_first_name, chat_title=safe_chat_title)


def render_missing_username_notice(policy: WelcomePolicy, *, first_name: str) -> str | None:
    if not policy.missing_username_notice:
        return None
    fallback = first_name or "朋友"
    return policy.missing_username_notice.format(first_name=fallback)
