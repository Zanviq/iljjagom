"""AI 세션/트레이스 라우터 — 관측(관리자) + ask_user 재개. 03-추가기능/02 §7.

- GET  /ai/sessions          : 세션 목록(관리자). status/bookId/limit 필터.
- GET  /ai/sessions/{id}     : 세션 상세 + 스텝(관리자).
- POST /ai/sessions/{id}/answer : ask_user 로 일시정지된 세션에 응답(책 소유 학생/관리자).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.deps import CurrentUser, get_current_user, get_store_dep, require_role
from app.errors import conflict, forbidden, not_found, validation_error
from app.models.schemas import (
    AiSessionDetail,
    AiSessionsResponse,
    AiSessionView,
    AiStepView,
    AnswerRequest,
    serialize,
)
from app.services.books import assert_can_access_book
from app.store.base import Store
from app.store.records import AiSessionRecord, AiStepRecord
from app.util import now_iso

router = APIRouter(tags=["ai"])


def _session_view(s: AiSessionRecord) -> AiSessionView:
    return AiSessionView(
        id=s.id, book_id=s.book_id, role=s.role, model=s.model, status=s.status,
        summary=s.summary, error=s.error, started_at=s.started_at, ended_at=s.ended_at,
    )


def _step_view(s: AiStepRecord) -> AiStepView:
    return AiStepView(
        idx=s.idx, thought=s.thought, skill=s.skill, args=s.args, observation=s.observation,
        tokens_in=s.tokens_in, tokens_out=s.tokens_out, ms=s.ms, created_at=s.created_at,
    )


@router.get("/ai/sessions")
async def list_sessions(
    book_id: str | None = Query(default=None, alias="bookId"),
    status: str | None = Query(default=None),
    role: str | None = Query(default=None),
    user_id: str | None = Query(default=None, alias="userId"),
    since: str | None = Query(default=None, alias="from"),
    until: str | None = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    sessions = store.list_ai_sessions(
        book_id=book_id, status=status, role=role, since=since, until=until, limit=limit
    )
    views = [_enrich_session(store, s) for s in sessions]
    # userId 필터(세션의 책 소유 학생 기준).
    if user_id:
        views = [v for v in views if v.user_id == user_id]
    return serialize(AiSessionsResponse(sessions=views))


def _enrich_session(store: Store, s: AiSessionRecord) -> AiSessionView:
    view = _session_view(s)
    # 책 소유 학생 → userId/userEmail.
    if s.book_id:
        book = store.get_book(s.book_id)
        if book:
            view.user_id = book.student_id
            prof = store.get_profile(book.student_id) if book.student_id else None
            view.user_email = prof.email if prof else None
    steps = store.list_ai_steps(s.id)
    view.step_count = len(steps)
    view.tokens_in = sum(st.tokens_in for st in steps)
    view.tokens_out = sum(st.tokens_out for st in steps)
    return view


@router.get("/ai/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: CurrentUser = Depends(require_role("admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    session = store.get_ai_session(session_id)
    if not session:
        raise not_found("세션을 찾을 수 없습니다.")
    steps = store.list_ai_steps(session_id)
    detail = AiSessionDetail(
        **_session_view(session).model_dump(),
        steps=[_step_view(s) for s in steps],
    )
    return serialize(detail)


@router.post("/ai/sessions/{session_id}/answer")
async def answer_session(
    session_id: str,
    req: AnswerRequest,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    """ask_user 로 일시정지(awaiting_user)된 세션에 사용자가 응답한다.

    응답을 messages 로 저장하고 스텝에 기록한 뒤 세션을 종료(done)한다.
    (완전한 ReAct 재진입은 후속 — 현재는 응답 수집·종결.)
    """
    session = store.get_ai_session(session_id)
    if not session:
        raise not_found("세션을 찾을 수 없습니다.")
    # 접근 제어: 책 소유 학생 또는 관리자(또는 담당 교사).
    if session.book_id:
        book = store.get_book(session.book_id)
        if not book:
            raise not_found("세션의 책을 찾을 수 없습니다.")
        assert_can_access_book(store, user, book)
    elif user.role != "admin":
        raise forbidden("이 세션에 응답할 수 없습니다.")

    if session.status != "awaiting_user":
        raise conflict("응답을 기다리는 세션이 아닙니다.")

    answer = (req.choice or req.text or "").strip()
    if not answer:
        raise validation_error("응답(choice 또는 text)이 필요합니다.")

    # 응답을 통합 대화(messages)로 저장 + 트레이스 스텝 기록.
    try:
        store.add_message(session.book_id, user.id, "user", "tutor", answer, session_id=session_id)
        steps = store.list_ai_steps(session_id)
        next_idx = (max((s.idx for s in steps), default=-1)) + 1
        store.add_ai_step(
            session_id, next_idx, "사용자 응답 수신", "user_answer",
            {"choice": req.choice, "text": req.text}, {"answer": answer},
        )
    except Exception:
        pass

    updated = store.update_ai_session(session_id, status="done", ended_at=now_iso())
    return serialize(_session_view(updated))
