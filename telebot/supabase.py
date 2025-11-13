"""Supabase integration utilities."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency guard for tests
    import httpx
except ImportError:  # pragma: no cover - defer requirement until runtime
    httpx = None  # type: ignore

from .config import Settings


DEFAULT_GROUP_CONFIG: Dict[str, Any] = {
    "banned_keywords": ["广告", "spam"],
    "auto_replies": [
        {
            "keyword": "签到",
            "reply": "输入 /checkin 开始签到，完成后可获得积分。",
            "delete_original": False,
        }
    ],
    "point_rules": [
        {
            "regex": r"[\\u4e00-\\u9fa5]{5,}",
            "points": 1,
        }
    ],
    "flood_control": {
        "enabled": True,
        "max_messages": 6,
        "interval_seconds": 20,
        "mute_seconds": 120,
        "notice": "消息过于频繁，已为你禁言 2 分钟。",
    },
    "welcome": {
        "enabled": True,
        "text": "欢迎 {mention} 加入 {chat_title}，请阅读置顶规则。",
        "require_username": False,
        "missing_username_notice": "请先设置 Telegram 用户名，方便管理员@你。",
    },
}


@dataclass
class CachedConfig:
    payload: Dict[str, Any]
    expires_at: float


@dataclass
class SupabaseConfigStore:
    """Fetch and persist group configuration via Supabase REST API."""

    settings: Settings
    _cache: Dict[int, CachedConfig] = field(default_factory=dict)
    _runtime_groups: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    _client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> Optional[httpx.AsyncClient]:
        if not self.settings.has_supabase:
            return None
        if httpx is None:
            raise RuntimeError("httpx is required for Supabase integration")
        if self._client is None:
            service_key = self.settings.supabase_service_role_key or ""
            headers = {
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(base_url=str(self.settings.supabase_url), headers=headers, timeout=15)
        return self._client

    async def fetch_group_config(self, chat_id: int) -> Dict[str, Any]:
        now = time.monotonic()
        cached = self._cache.get(chat_id)
        if cached and cached.expires_at > now:
            return cached.payload

        if chat_id in self._runtime_groups:
            payload = self._runtime_groups[chat_id]
        elif self.client:
            payload = await self._fetch_from_supabase(chat_id)
        else:
            payload = DEFAULT_GROUP_CONFIG

        self._cache[chat_id] = CachedConfig(payload=payload, expires_at=now + self.settings.config_cache_seconds)
        return payload

    async def _fetch_from_supabase(self, chat_id: int) -> Dict[str, Any]:
        assert self.client is not None
        path = f"/rest/v1/group_configs?select=*&chat_id=eq.{chat_id}&limit=1"
        response = await self.client.get(path)
        response.raise_for_status()
        data = response.json()
        if not data:
            return DEFAULT_GROUP_CONFIG
        record = data[0]
        if isinstance(record.get("payload"), str):
            return json.loads(record["payload"])
        return record.get("payload", DEFAULT_GROUP_CONFIG)

    async def record_action(self, chat_id: int, user_id: int, action: str, payload: Dict[str, Any]) -> None:
        if not self.client:
            # fallback: keep it in-memory for debugging & tests
            key = (chat_id, user_id)
            bucket = self._runtime_groups.setdefault(chat_id, DEFAULT_GROUP_CONFIG | {"audit_log": []})
            bucket.setdefault("audit_log", []).append({"user_id": user_id, "action": action, "payload": payload})
            return

        assert self.client is not None
        document = {
            "chat_id": chat_id,
            "user_id": user_id,
            "action": action,
            "payload": payload,
        }
        response = await self.client.post("/rest/v1/action_logs", content=json.dumps(document))
        response.raise_for_status()

    async def increment_points(self, chat_id: int, user_id: int, amount: int) -> None:
        if not self.client:
            bucket = self._runtime_groups.setdefault(chat_id, DEFAULT_GROUP_CONFIG | {"points": {}})
            bucket.setdefault("points", {})
            bucket["points"][user_id] = bucket["points"].get(user_id, 0) + amount
            return

        assert self.client is not None
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
            "delta": amount,
        }
        response = await self.client.post("/rest/v1/rpc/increment_points", content=json.dumps(payload))
        response.raise_for_status()

    async def get_points(self, chat_id: int, user_id: int) -> int:
        if not self.client:
            bucket = self._runtime_groups.get(chat_id, {})
            points = bucket.get("points", {})
            return int(points.get(user_id, 0))

        assert self.client is not None
        path = (
            f"/rest/v1/points_balances?select=balance&chat_id=eq.{chat_id}&user_id=eq.{user_id}&limit=1"
        )
        response = await self.client.get(path)
        response.raise_for_status()
        data = response.json()
        if not data:
            return 0
        record = data[0]
        balance = record.get("balance", 0)
        return int(balance or 0)

    def seed_group_config(self, chat_id: int, payload: Dict[str, Any]) -> None:
        """Utility for tests: seed an in-memory group configuration."""

        self._runtime_groups[chat_id] = payload

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


async def shutdown(store: SupabaseConfigStore) -> None:
    await store.close()
    # HTTPX fails to close if called twice; ensure graceful shutdown.
    await asyncio.sleep(0)
