"""챕터 라우터 — 집필 SSE 스트림, 수정 요청(P2)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.ai.gemini import GeminiClient, get_gemini
from app.deps import CurrentUser, get_current_user, get_store_dep, require_role
from app.models.schemas import ReviseRequest, ReviseResponse, serialize
from app.services import chapters
from app.store.base import Store

router = APIRouter(tags=["chapters"])


@router.get("/books/{book_id}/chapters/{idx}/stream")
async def stream_chapter(
    book_id: str,
    idx: int,
    from_: int = Query(0, alias="from", ge=0),
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
) -> StreamingResponse:
    generator = chapters.stream_chapter(store, gemini, user, book_id, idx, from_)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 버퍼링 비활성(스트림 즉시 전송)
        },
    )


@router.post("/books/{book_id}/chapters/{idx}/revise", status_code=202)
async def revise_chapter(
    book_id: str,
    idx: int,
    req: ReviseRequest,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    # P2: 대화 AI → 집필 → 편집 검수 파이프라인. P1 에서는 계약 형태만 제공.
    return serialize(ReviseResponse(status="revising"))
