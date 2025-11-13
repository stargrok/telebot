"""Environment driven configuration for Telebot without external dependencies."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


@dataclass(slots=True)
class Settings:
    api_id: int = 0
    api_hash: str = ""
    bot_token: str = ""
    supabase_url: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    config_cache_seconds: int = 60
    default_language: str = "zh"

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def load_settings() -> Settings:
    """Load settings from environment variables only once."""

    return Settings(
        api_id=int(os.getenv("TELEGRAM_API_ID", "0")),
        api_hash=os.getenv("TELEGRAM_API_HASH", ""),
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
        config_cache_seconds=int(os.getenv("CONFIG_CACHE_SECONDS", "60")),
        default_language=os.getenv("DEFAULT_LANGUAGE", "zh"),
    )
