import asyncio

from telebot.config import Settings
from telebot.supabase import SupabaseConfigStore


def test_in_memory_points_balance_roundtrip():
    settings = Settings()
    store = SupabaseConfigStore(settings)

    async def scenario():
        assert await store.get_points(1, 99) == 0
        await store.increment_points(1, 99, 5)
        await store.increment_points(1, 99, 2)
        assert await store.get_points(1, 99) == 7

    asyncio.run(scenario())
