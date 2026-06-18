"""기획/설계 라우터 — 기획 인터뷰 대화, Bible 설계."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Response

from app.ai.gemini import GeminiClient, get_gemini
from app.deps import CurrentUser, get_store_dep, require_guardian_consent, require_role
from app.models.schemas import PlanMessageRequest, serialize
from app.ratelimit import rate_limit
from app.services import books
from app.store.base import Store

router = APIRouter(tags=["planning"])


@router.post("/books/{book_id}/plan/messages")
async def plan_message(
    book_id: str,
    req: PlanMessageRequest,
    background: BackgroundTasks,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
    _rl: None = Depends(rate_limit("plan", 60)),
    _consent: CurrentUser = Depends(require_guardian_consent()),
) -> dict:
    reply = await books.plan_message(store, gemini, user, book_id, req.message)
    # readyToWrite 도달 → Bible 백그라운드 선생성(버튼 클릭 시 즉시 진입, 학생/04).
    if reply.ready_to_write:
        background.add_task(books.prefetch_design, store, gemini, book_id)
    return serialize(reply)


@router.post("/books/{book_id}/design", status_code=202)
async def design(
    book_id: str,
    response: Response,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
    _rl: None = Depends(rate_limit("design", 10)),
) -> dict:
    result = await books.design_book(store, gemini, user, book_id)
    return serialize(result)
