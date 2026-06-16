"""저장소 팩토리.

Supabase 자격이 있으면 SupabaseStore, 없으면 InMemoryStore 를 쓴다.
서비스/엔드포인트는 동일한 Store 인터페이스만 본다.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.store.base import Store


@lru_cache
def get_store() -> Store:
    settings = get_settings()
    if settings.use_supabase:
        from app.store.supabase_store import SupabaseStore

        return SupabaseStore(settings)
    from app.store.memory import InMemoryStore

    return InMemoryStore()
