"""사용자별 호출 한도(비용 가드레일) — AI 비용이 큰 엔드포인트 보호.

무상태화(03-추가기능/01 §3.4): 카운터는 Store.rate_hit() 가 보관한다.
- SupabaseStore: rate_hits 테이블(멀티 워커에서도 한도 정합).
- InMemoryStore: 프로세스 deque(개발/테스트).
한도값(limit/window)은 `app_settings.rate_limits` 에서 읽어 관리자가 런타임 조정 가능.
설정은 짧은 TTL 캐시(매 요청 DB 조회 회피). 초과 시 429 rate_limited(§4.1).
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends

from app.deps import CurrentUser, get_current_user, get_store_dep
from app.errors import rate_limited
from app.store.base import Store

# app_settings.rate_limits 짧은 TTL 캐시 — (조회시각, 값)
_settings_cache: dict[str, Any] = {"at": 0.0, "value": None}
_SETTINGS_TTL = 30.0


def reset() -> None:
    """테스트/운영 초기화용 — 설정 캐시만 비운다.

    실제 호출 카운터는 Store 인스턴스에 있으므로 store 재생성으로 초기화된다.
    """
    _settings_cache["at"] = 0.0
    _settings_cache["value"] = None


def _rate_limit_config(store: Store) -> dict[str, Any]:
    now = time.monotonic()
    cached = _settings_cache["value"]
    if cached is not None and now - _settings_cache["at"] < _SETTINGS_TTL:
        return cached
    try:
        value = store.get_setting("rate_limits") or {}
    except Exception:
        value = {}
    if not isinstance(value, dict):
        value = {}
    _settings_cache["value"] = value
    _settings_cache["at"] = now
    return value


def rate_limit(
    bucket: str, limit: int, window: float = 60.0
) -> Callable[[CurrentUser, Store], Awaitable[None]]:
    """사용자별 window 초 동안 limit 회로 제한하는 FastAPI 의존성을 만든다.

    전달된 limit/window 는 폴백 기본값. app_settings.rate_limits[bucket] 이 있으면 그 값을 우선한다.
    """

    async def _dep(
        user: CurrentUser = Depends(get_current_user),
        store: Store = Depends(get_store_dep),
    ) -> None:
        cfg = _rate_limit_config(store).get(bucket) or {}
        eff_limit = int(cfg.get("limit", limit))
        eff_window = float(cfg.get("window", window))
        count = store.rate_hit(bucket, user.id, eff_window)
        if count > eff_limit:
            raise rate_limited("요청이 너무 잦아요. 잠시 후 다시 시도해 주세요.")

    return _dep
