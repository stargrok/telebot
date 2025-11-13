"""Telethon powered application entrypoint."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import ChatAdminRequiredError

from .config import Settings, load_settings
from .rules import Action, ActionType, RuleEngine
from .supabase import SupabaseConfigStore
from .flood import FloodProtector
from .welcome import load_welcome_policy, render_missing_username_notice, render_welcome_message


class TelebotApplication:
    """High level wrapper that wires Telethon events with the rule engine."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.client = TelegramClient("telebot", self.settings.api_id, self.settings.api_hash)
        self.store = SupabaseConfigStore(self.settings)
        self._handlers_registered = False
        self._flood_protector = FloodProtector()

    def register_handlers(self) -> None:
        if self._handlers_registered:
            return

        @self.client.on(events.NewMessage(pattern=r"/checkin"))
        async def _(event: events.NewMessage.Event) -> None:  # pragma: no cover - Telethon runtime
            await self.store.increment_points(event.chat_id, event.sender_id, 5)
            await event.respond("✅ 签到成功，本次获得 5 积分。")

        @self.client.on(events.NewMessage(pattern=r"/me"))
        async def _me(event: events.NewMessage.Event) -> None:  # pragma: no cover - Telethon runtime
            chat_id = event.chat_id
            user_id = event.sender_id or 0
            points = await self.store.get_points(chat_id, user_id)
            await event.respond(f"📊 当前积分：{points}")

        @self.client.on(events.ChatAction())
        async def handle_join(event: events.ChatAction.Event) -> None:  # pragma: no cover - Telethon runtime
            if not (event.user_joined or event.user_added):
                return
            config = await self.store.fetch_group_config(event.chat_id)
            policy = load_welcome_policy(config.get("welcome"))
            if not policy.enabled:
                return
            user = await event.get_user()
            if user is None:
                return
            if policy.require_username and not getattr(user, "username", None):
                notice = render_missing_username_notice(policy, first_name=user.first_name or "")
                if notice:
                    await event.respond(notice)
                return
            chat = await event.get_chat()
            message = render_welcome_message(
                policy,
                mention=self._format_mention(user),
                first_name=user.first_name or "",
                chat_title=getattr(chat, "title", "本群"),
            )
            await event.respond(message)

        @self.client.on(events.NewMessage())
        async def handle_message(event: events.NewMessage.Event) -> None:  # pragma: no cover - Telethon runtime
            if not event.raw_text:
                return
            chat_id = event.chat_id
            user_id = event.sender_id or 0
            config = await self.store.fetch_group_config(chat_id)
            flood_action = self._flood_protector.check(chat_id, user_id, config.get("flood_control"))
            if flood_action:
                await self._apply_action(flood_action.type, event, flood_action, chat_id, user_id, reason="flood_control")
                return
            engine = RuleEngine.from_config(config)
            matches = engine.match(event.raw_text)
            if not matches:
                return
            message_deleted = False
            for match in matches:
                if match.rule.delete_original and not message_deleted:
                    await self._delete_message(event, chat_id, user_id, reason=match.rule.name)
                    message_deleted = True
                await self._apply_action(match.action.type, event, match.action, chat_id, user_id, reason=match.rule.name, already_deleted=message_deleted)
                if match.action.type is ActionType.DELETE:
                    message_deleted = True

        self._handlers_registered = True

    async def _apply_action(
        self,
        action_type: ActionType,
        event: events.NewMessage.Event,
        action: Action,
        chat_id: int,
        user_id: int,
        *,
        reason: str | None = None,
        already_deleted: bool = False,
    ) -> None:
        if action_type is ActionType.DELETE:
            if not already_deleted:
                await self._delete_message(event, chat_id, user_id, reason=reason)
        elif action_type is ActionType.REPLY:
            if action.message:
                await event.respond(action.message)
        elif action_type is ActionType.MUTE:
            await self._mute_member(event, duration=action.duration or 60, notice=action.message)
        elif action_type is ActionType.ADD_POINTS:
            await self.store.increment_points(chat_id, user_id, action.points or 1)

    async def _delete_message(self, event: events.NewMessage.Event, chat_id: int, user_id: int, *, reason: str | None) -> None:
        await event.delete()
        await self.store.record_action(
            chat_id,
            user_id,
            "delete",
            {"message_id": event.id, "reason": reason or "rule"},
        )

    async def _mute_member(self, event: events.NewMessage.Event, duration: int, notice: str | None) -> None:
        chat = await event.get_chat()
        sender = await event.get_sender()
        if sender is None:
            return
        until = datetime.now(tz=timezone.utc) + timedelta(seconds=duration)
        try:
            await self.client.edit_permissions(chat, sender, send_messages=False, until_date=until)
        except ChatAdminRequiredError:  # pragma: no cover - runtime guard
            return
        if notice:
            await event.respond(notice)

    async def start(self) -> None:  # pragma: no cover - requires Telegram credentials
        self.register_handlers()
        await self.client.start(bot_token=self.settings.bot_token)
        await self.client.run_until_disconnected()

    async def shutdown(self) -> None:
        await self.store.close()
        await self.client.disconnect()

    @staticmethod
    def _format_mention(user: object) -> str:
        username = getattr(user, "username", None)
        if username:
            return f"@{username}"
        first = (getattr(user, "first_name", "") or "").strip()
        last = (getattr(user, "last_name", "") or "").strip()
        full = " ".join(filter(None, [first, last])).strip()
        return full or "新成员"


def run() -> None:  # pragma: no cover - CLI helper
    app = TelebotApplication()
    asyncio.run(app.start())
