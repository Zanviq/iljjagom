"""책 서비스 — 생성/조회/기획대화/설계(Bible). FR-S1~S3."""
from __future__ import annotations

from app.ai import chat, designer, rag
from app.ai.gemini import GeminiClient
from app.ai.safety import check_input
from app.deps import CurrentUser
from app.errors import forbidden, not_found, validation_error
from app.models.schemas import (
    Book,
    BookDetail,
    ChapterMeta,
    DesignResponse,
    PlanReply,
)
from app.store.base import Store
from app.store.records import BookRecord


# --- 접근 제어 (RLS 등가, 서비스 계층) ---
def assert_can_access_book(store: Store, user: CurrentUser, book: BookRecord) -> None:
    if user.role == "admin":
        return
    if book.student_id == user.id:
        return
    if book.classroom_id:
        classroom = store.get_classroom(book.classroom_id)
        if classroom and classroom.teacher_id == user.id:
            return
    raise forbidden("이 책에 접근할 수 없습니다.")


def assert_owner_student(user: CurrentUser, book: BookRecord) -> None:
    if book.student_id != user.id:
        raise forbidden("자기 책에만 할 수 있는 작업입니다.")


def get_book_or_404(store: Store, book_id: str) -> BookRecord:
    book = store.get_book(book_id)
    if not book:
        raise not_found("책을 찾을 수 없습니다.")
    return book


def _to_book(rec: BookRecord) -> Book:
    return Book(
        id=rec.id,
        prompt_id=rec.prompt_id,
        class_id=rec.classroom_id,
        status=rec.status,
        title=rec.title,
        created_at=rec.created_at,
    )


# --- FR-S1 책 생성 ---
def create_book(store: Store, user: CurrentUser, prompt_id: str) -> Book:
    prompt = store.get_prompt(prompt_id)
    if not prompt:
        raise not_found("발제를 찾을 수 없습니다.")
    # 학생은 자기 학급의 발제로만 책을 만들 수 있다.
    if user.role != "admin" and not store.is_enrolled(prompt.classroom_id, user.id):
        raise forbidden("이 발제가 속한 학급의 학생이 아닙니다.")
    rec = store.create_book(
        student_id=user.id, classroom_id=prompt.classroom_id, prompt_id=prompt_id
    )
    return _to_book(rec)


# --- GET /books/{id} ---
def get_book_detail(store: Store, user: CurrentUser, book_id: str) -> BookDetail:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)
    chapters = [
        ChapterMeta(
            idx=c.idx,
            mode=c.mode,
            review_status=c.review_status,
            has_illustration=bool(c.illustration_path),
        )
        for c in store.list_chapters(book_id)
    ]
    return BookDetail(
        id=book.id,
        status=book.status,
        title=book.title,
        prompt_id=book.prompt_id,
        class_id=book.classroom_id,
        chapters=chapters,
        total_chapters_planned=book.total_chapters_planned,
    )


# --- FR-S2 기획 인터뷰 대화 ---
async def plan_message(
    store: Store, gemini: GeminiClient, user: CurrentUser, book_id: str, message: str
) -> PlanReply:
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book)

    safety = check_input(message)
    if safety.risk:
        store.add_safety_flag(book_id, user.id, "plan", "정서 위험 신호 감지")
    if not safety.ok:
        raise validation_error(safety.reason, {"suggestion": safety.suggestion})

    store.add_plan_message(book_id, "student", message)
    student_messages = [m.content for m in store.list_plan_messages(book_id) if m.role == "student"]
    reply = await chat.interview_reply(gemini, student_messages, message)
    store.add_plan_message(book_id, "interviewer", reply.reply)
    return reply


# --- FR-S3 설계(Bible 생성) ---
async def design_book(
    store: Store, gemini: GeminiClient, user: CurrentUser, book_id: str
) -> DesignResponse:
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book)

    existing = store.get_bible(book_id)
    if existing:
        total = existing.data.get("totalChaptersPlanned")
        return DesignResponse(status="done", total_chapters_planned=total)

    prompt = store.get_prompt(book.prompt_id) if book.prompt_id else None
    student_messages = [m.content for m in store.list_plan_messages(book_id) if m.role == "student"]
    traits = chat._extract_draft(student_messages).traits

    bible = await designer.build_bible(gemini, prompt, student_messages, traits)
    store.upsert_bible(book_id, bible)

    # 챕터 골격 생성(이벤트 분배 기준).
    events = bible.get("events", [])
    total = bible.get("totalChaptersPlanned", len(events) or designer.DEFAULT_TOTAL_CHAPTERS)
    for ev in events:
        idx = ev.get("chapterIdx")
        mode = ev.get("mode", "free")
        if idx and not store.get_chapter(book_id, idx):
            store.create_chapter(book_id, idx, mode)

    store.update_book(
        book_id,
        status="writing",
        title=bible.get("title"),
        total_chapters_planned=total,
    )

    # Bible 핵심 텍스트를 RAG 인덱스에 적재(설계 단계 분량).
    await _index_bible(store, gemini, book_id, bible)

    return DesignResponse(status="done", total_chapters_planned=total)


async def _index_bible(store: Store, gemini: GeminiClient, book_id: str, bible: dict) -> None:
    texts: list[str] = []
    for c in bible.get("characters", []):
        traits = ", ".join(c.get("traits", []))
        texts.append(f"인물 {c.get('name')}: {traits}. 외형 {c.get('appearance', '')}")
    world = bible.get("world", {})
    if world:
        texts.append(f"세계관: {world.get('setting', '')} / 분위기 {world.get('tone', '')}")
    for ev in bible.get("events", []):
        texts.append(f"{ev.get('chapterIdx')}장 개요: {ev.get('summary', '')}")
    for t in texts:
        await rag.index_text(store, gemini, book_id, None, t)
