"""챕터 라우터 — 집필 SSE 스트림, 수정 요청(P2)."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.ai.gemini import GeminiClient, get_gemini
from app.ai.safety import check_input
from app.deps import (
    CurrentUser,
    get_current_user,
    get_store_dep,
    require_guardian_consent,
    require_role,
)
from app.errors import conflict, validation_error
from app.models.schemas import ReviseRequest, ReviseResponse, serialize
from app.ratelimit import rate_limit
from app.services import books, chapters
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
        # 스트림 종료 후(비동기, 학생 대기 미노출): 현재 장 검수 → 다음 장 백그라운드 선생성(P1-06).
        background=BackgroundTask(
            chapters.post_stream_tasks, store, gemini, book_id, idx
        ),
    )


@router.post("/books/{book_id}/chapters/{idx}/revise", status_code=202)
async def revise_chapter(
    book_id: str,
    idx: int,
    req: ReviseRequest,
    background: BackgroundTasks,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
    _rl: None = Depends(rate_limit("revise", 20)),
    _consent: CurrentUser = Depends(require_guardian_consent()),
) -> dict:
    # 소유 학생만(또는 admin). 집필된 챕터만 수정 가능.
    book = books.get_book_or_404(store, book_id)
    if user.role != "admin":
        books.assert_owner_student(user, book)
    chapter = store.get_chapter(book_id, idx)
    if not chapter or chapter.char_count == 0:
        raise conflict("아직 집필되지 않은 챕터는 수정할 수 없습니다.")

    # 입력 안전 게이트(기획 대화와 동일 규약).
    safety = check_input(req.instruction)
    if safety.risk:
        store.add_safety_flag(book_id, user.id, "revise", "정서 위험 신호 감지")
    if not safety.ok:
        raise validation_error(safety.reason, {"suggestion": safety.suggestion})

    # 해석→재생성→편집검수→반영은 백그라운드로. 완료는 stream 재구독 또는 book 폴링으로 확인(§4.2).
    background.add_task(chapters.run_revise, store, gemini, book_id, idx, req.instruction)
    return serialize(ReviseResponse(status="revising"))
