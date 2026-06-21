"""AI 세션/트레이스 라우터 — 관측(관리자) + ask_user 재개. 03-추가기능/02 §7.

- GET  /ai/sessions          : 세션 목록(관리자). status/bookId/limit 필터.
- GET  /ai/sessions/{id}     : 세션 상세 + 스텝(관리자).
- POST /ai/sessions/{id}/answer : ask_user 로 일시정지된 세션에 응답(책 소유 학생/관리자).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.ai.gemini import GeminiClient, get_gemini
from app.config import Settings, get_settings
from app.deps import (
    CurrentUser,
    get_current_user,
    get_store_dep,
    require_guardian_consent,
    require_role,
)
from app.errors import conflict, forbidden, not_found, validation_error
from app.models.schemas import (
    AdminMessage,
    AiSessionDetail,
    AiSessionsResponse,
    AiSessionView,
    AiStepView,
    AnswerRequest,
    OverseerMessageRequest,
    SessionContext,
    serialize,
)
from app.ratelimit import rate_limit
from app.services import overseer as overseer_svc
from app.services.admin import _STAGE_LABEL
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


# role → 사람이 읽는 단계 라벨은 services.admin 의 _STAGE_LABEL 을 단일 출처로 공유한다.
def _stage_label(role: str | None) -> str | None:
    return _STAGE_LABEL.get(role or "", role)


def _enrich_session(store: Store, s: AiSessionRecord) -> AiSessionView:
    view = _session_view(s)
    view.stage = _stage_label(s.role)
    # 책 소유 학생 → userId/userEmail + 책 제목·상태. book 없는 세션은 session.user_id 로.
    owner_id = None
    if s.book_id:
        book = store.get_book(s.book_id)
        if book:
            owner_id = book.student_id
            view.book_title = book.title
            view.book_status = book.status
    if not owner_id:
        owner_id = s.user_id
    if owner_id:
        view.user_id = owner_id
        prof = store.get_profile(owner_id)
        view.user_email = prof.email if prof else None
    steps = store.list_ai_steps(s.id)
    view.step_count = len(steps)
    view.tokens_in = sum(st.tokens_in for st in steps)
    view.tokens_out = sum(st.tokens_out for st in steps)
    return view


def _admin_message_view(store: Store, m) -> AdminMessage:
    prof = store.get_profile(m.user_id) if m.user_id else None
    return AdminMessage(
        id=m.id, book_id=m.book_id, user_id=m.user_id,
        user_email=prof.email if prof else None,
        role=m.role, kind=m.kind, content=m.content,
        session_id=m.session_id, created_at=m.created_at,
    )


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
    enriched = _enrich_session(store, session)  # userEmail·bookTitle·stage 포함
    transcript = [_admin_message_view(store, m) for m in store.list_messages_for_session(session_id)]
    detail = AiSessionDetail(
        **enriched.model_dump(),
        steps=[_step_view(s) for s in steps],
        transcript=transcript,
        context=SessionContext(
            user_email=enriched.user_email, book_id=session.book_id,
            book_title=enriched.book_title, stage=enriched.stage,
        ),
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


@router.post("/ai/overseer/messages")
async def overseer_messages(
    req: OverseerMessageRequest,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
    settings: Settings = Depends(get_settings),
    _rl: None = Depends(rate_limit("overseer", 60)),
    _consent: CurrentUser = Depends(require_guardian_consent()),
) -> dict:
    """총괄(곰 작가) AI 채팅 — 학생 본인 데이터를 읽고 화면 이동/책 생성 액션을 돌려준다.

    role="overseer" ReAct 세션으로 처리(스텝 ai_steps, 대화 messages kind="overseer").
    입력은 안전 게이트 통과, 액션 `to` 는 화이트리스트 라우트만. 03-총괄AI-사이드바.
    """
    reply = await overseer_svc.overseer_message(
        store, gemini, settings, user, req.message, req.session_id, req.route
    )
    return serialize(reply)
