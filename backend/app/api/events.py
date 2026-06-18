"""측정 라우터 — 행동 로그 배치 수집. 추가기능 04 §3.2."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_store_dep, require_role
from app.models.schemas import EventsRequest, EventsResponse, serialize
from app.ratelimit import rate_limit
from app.services import events as svc
from app.store.base import Store

router = APIRouter(tags=["events"])


@router.post("/events", status_code=202)
async def post_events(
    req: EventsRequest,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    _rl: None = Depends(rate_limit("events", 120)),
) -> dict:
    accepted = svc.record_events(store, user, req.events)
    return serialize(EventsResponse(accepted=accepted))
