"""관리자 라우터 — 사용량 집계 + 사용자/메시지 관리 (FR-M1, 추가기능 06)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.config import Settings, get_settings
from app.deps import CurrentUser, get_store_dep, require_role
from app.models.schemas import AdminUsageResponse, AdminUserPatch, SettingPut, serialize
from app.services import admin as svc
from app.store.base import Store

router = APIRouter(tags=["admin"])


@router.get("/admin/usage")
async def usage(
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    counts = store.usage_counts()
    return serialize(AdminUsageResponse(**counts))


@router.get("/admin/users")
async def list_users(
    query: str | None = Query(default=None),
    role: str | None = Query(default=None),
    class_id: str | None = Query(default=None, alias="classId"),
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.list_users(store, query, role, class_id))


@router.patch("/admin/users/{user_id}")
async def patch_user(
    user_id: str,
    patch: AdminUserPatch,
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.patch_user(store, user, user_id, patch))


@router.post("/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return svc.deactivate_user(store, user, user_id)


@router.get("/admin/messages")
async def list_messages(
    user_id: str | None = Query(default=None, alias="userId"),
    book_id: str | None = Query(default=None, alias="bookId"),
    kind: str | None = Query(default=None),
    since: str | None = Query(default=None, alias="from"),
    until: str | None = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.list_messages(store, user_id, book_id, kind, since, until, limit))


@router.get("/admin/settings")
async def get_settings_view(
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
    settings: Settings = Depends(get_settings),
) -> dict:
    return serialize(svc.get_settings_view(store, settings))


@router.put("/admin/settings")
async def put_settings(
    payload: SettingPut,
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.put_settings(store, user, payload))


@router.get("/admin/usage/tokens")
async def usage_tokens(
    group_by: str = Query(default="model", alias="groupBy"),
    since: str | None = Query(default=None, alias="from"),
    until: str | None = Query(default=None, alias="to"),
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.token_usage(store, group_by, since, until))
