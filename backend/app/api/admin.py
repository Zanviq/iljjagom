"""관리자 라우터 — 사용량/안전 신호 집계 (FR-M1, 최소)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_store_dep, require_role
from app.models.schemas import AdminUsageResponse, serialize
from app.store.base import Store

router = APIRouter(tags=["admin"])


@router.get("/admin/usage")
async def usage(
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    counts = store.usage_counts()
    return serialize(AdminUsageResponse(**counts))
