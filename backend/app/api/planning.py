"""기획/설계 라우터 — 기획 인터뷰 대화, Bible 설계."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.ai.gemini import GeminiClient, get_gemini
from app.deps import CurrentUser, get_store_dep, require_role
from app.models.schemas import PlanMessageRequest, serialize
from app.services import books
from app.store.base import Store

router = APIRouter(tags=["planning"])


@router.post("/books/{book_id}/plan/messages")
async def plan_message(
    book_id: str,
    req: PlanMessageRequest,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
) -> dict:
    reply = await books.plan_message(store, gemini, user, book_id, req.message)
    return serialize(reply)


@router.post("/books/{book_id}/design", status_code=202)
async def design(
    book_id: str,
    response: Response,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
) -> dict:
    result = await books.design_book(store, gemini, user, book_id)
    return serialize(result)
