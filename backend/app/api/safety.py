"""안전 검토 라우터 — 교사/관리자의 안전 신호·보류 편지 검토. 추가기능 03 §4.3.

전부 teacher/admin 전용. 서비스 계층에서 학급/책 범위를 추가 검사(RLS 이중 보장).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.ai.gemini import GeminiClient, get_gemini
from app.deps import CurrentUser, get_store_dep, require_role
from app.models.schemas import (
    LetterApproveRequest,
    LetterRejectRequest,
    ResolveRequest,
    serialize,
)
from app.services import safety as svc
from app.store.base import Store

router = APIRouter(tags=["safety"])


@router.get("/classes/{class_id}/safety-flags")
async def class_flags(
    class_id: str,
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.list_class_flags(store, user, class_id, status, source))


@router.get("/admin/safety-flags")
async def admin_flags(
    status: str | None = Query(default=None),
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.list_admin_flags(store, status))


@router.get("/safety-flags/{flag_id}")
async def flag_detail(
    flag_id: str,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.get_flag_detail(store, user, flag_id))


@router.post("/safety-flags/{flag_id}/resolve")
async def resolve_flag(
    flag_id: str,
    req: ResolveRequest,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.resolve_flag(store, user, flag_id, req.note))


@router.get("/classes/{class_id}/letters")
async def class_letters(
    class_id: str,
    status: str | None = Query(default=None),
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.list_class_letters(store, user, class_id, status))


@router.post("/letters/{letter_id}/approve")
async def approve_letter(
    letter_id: str,
    req: LetterApproveRequest,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
) -> dict:
    letter = await svc.approve_letter(
        store, gemini, user, letter_id, req.reply, req.use_ai_reply
    )
    return serialize(letter)


@router.post("/letters/{letter_id}/reject")
async def reject_letter(
    letter_id: str,
    req: LetterRejectRequest,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(svc.reject_letter(store, user, letter_id, req.note))
