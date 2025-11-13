"""Anti-flood helper used to detect message spamming."""

from __future__ import annotations

from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Deque, Dict, Tuple

from .rules import Action, ActionType


@dataclass(slots=True)
class FloodConfig:
    enabled: bool = False
    max_messages: int = 5
    interval_seconds: int = 30
    mute_seconds: int = 60
    notice: str | None = None


class FloodProtector:
    """Track user activity per chat and return punishment actions when needed."""

    def __init__(self) -> None:
        self._messages: Dict[Tuple[int, int], Deque[float]] = defaultdict(deque)

    def check(self, chat_id: int, user_id: int, config: dict | None, *, now: float | None = None) -> Action | None:
        cfg = FloodConfig(**config) if config else FloodConfig()
        if not cfg.enabled:
            return None
        key = (chat_id, user_id)
        bucket = self._messages[key]
        current_ts = now if now is not None else self._now()
        self._trim(bucket, cfg.interval_seconds, current_ts)
        bucket.append(current_ts)
        if len(bucket) > cfg.max_messages:
            bucket.clear()
            return Action(type=ActionType.MUTE, duration=cfg.mute_seconds, message=cfg.notice)
        return None

    @staticmethod
    def _trim(bucket: Deque[float], interval: int, current_ts: float) -> None:
        while bucket and current_ts - bucket[0] > interval:
            bucket.popleft()

    @staticmethod
    def _now() -> float:
        from time import monotonic

        return monotonic()
