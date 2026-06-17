"""사용자별 호출 한도(비용 가드레일) — AI 비용이 큰 엔드포인트 보호.

인메모리 고정 윈도(슬라이딩) 방식. 초과 시 429 rate_limited(§4.1).
멀티 프로세스/영속 한도는 P4 운영에서 Redis 등으로 확장(현재는 단일 프로세스 가드).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Depends

from app.deps import CurrentUser, get_current_user
from app.errors import rate_limited

# (bucket, user_id) -> 최근 호출 시각(monotonic) 큐
_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def reset() -> None:
    """테스트/운영 초기화용."""
    _hits.clear()


def rate_limit(
    bucket: str, limit: int, window: float = 60.0
) -> Callable[[CurrentUser], Awaitable[None]]:
    """사용자별 window 초 동안 limit 회로 제한하는 FastAPI 의존성을 만든다."""

    async def _dep(user: CurrentUser = Depends(get_current_user)) -> None:
        now = time.monotonic()
        dq = _hits[(bucket, user.id)]
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= limit:
            raise rate_limited("요청이 너무 잦아요. 잠시 후 다시 시도해 주세요.")
        dq.append(now)

    return _dep
