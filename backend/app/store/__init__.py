"""저장소 팩토리.

정책(03-추가기능/01 §3.1): SupabaseStore 가 기본. InMemoryStore 는 테스트 전용.
- Supabase 자격이 있으면 SupabaseStore.
- 자격이 없고 prod 면 기동 거부(fail-closed).
- 자격이 없고 test/dev 면 인메모리 폴백(dev 는 경고 로그).
서비스/엔드포인트는 동일한 Store 인터페이스만 본다.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings
from app.store.base import Store

logger = logging.getLogger("app.store")


@lru_cache
def get_store() -> Store:
    settings = get_settings()
    if settings.use_supabase:
        from app.store.supabase_store import SupabaseStore

        return SupabaseStore(settings)

    # 자격 없음 — 인메모리 폴백 정책
    if not settings.in_memory_allowed:
        raise RuntimeError(
            "운영(APP_ENV=prod)에서 Supabase 자격이 없습니다. "
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 를 설정하세요."
        )
    if not settings.is_test:
        logger.warning(
            "Supabase 미설정 — 인메모리 저장소 폴백(개발 전용, 영속화 안 됨)."
        )
    from app.store.memory import InMemoryStore

    return InMemoryStore()
