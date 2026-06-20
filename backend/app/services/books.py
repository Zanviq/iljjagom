"""책 서비스 — 생성/조회/기획대화/설계(Bible). FR-S1~S3."""
from __future__ import annotations

import hashlib

from app.ai import chat, designer, rag
from app.ai.gemini import GeminiClient
from app.ai.safety import check_input
from app.ai.skills.base import estimate_tokens
from app.ai.trace import Trace
from app.deps import CurrentUser
from app.errors import conflict, forbidden, not_found, validation_error
from app.models.schemas import (
    BibleResponse,
    Book,
    BookDetail,
    BooksResponse,
    BookSummary,
    ChapterContent,
    ChapterMeta,
    ChaptersContentResponse,
    DesignResponse,
    PlanMessagesResponse,
    PlanMessageView,
    PlanReply,
    StudentBooksResponse,
)
from app.services.prefetch import acquire_prefetch, release_prefetch
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
    if getattr(prompt, "status", "open") == "closed":
        raise conflict("마감된 발제로는 새 이야기를 만들 수 없어요.")
    rec = store.create_book(
        student_id=user.id, classroom_id=prompt.classroom_id, prompt_id=prompt_id
    )
    return _to_book(rec)


# --- GET /books (내 책 목록/이어 읽기) ---
def _resume_for(store: Store, rec) -> tuple[int | None, str | None, str | None]:
    """이어가기 목적지(05-기능수정 §03): (현재 챕터 idx, mode, stage).

    plan → collab(미완 free) → mid_activity(기·승 후 필수) → read(전·결) → done 순.
    """
    from app.services import midactivity
    from app.services.collab import COLLAB_TARGET_PARAGRAPHS

    if rec.status == "planning":
        return 1, "free", "plan"
    chapters = sorted(store.list_chapters(rec.id), key=lambda c: c.idx)
    if not chapters:
        return None, None, None
    # 미완 free 챕터(기·승) → 협업 이어쓰기.
    for c in chapters:
        if c.mode == "free" and len(store.list_paragraphs(c.id)) < COLLAB_TARGET_PARAGRAPHS:
            return c.idx, "free", "collab"
    # 기·승 끝 + 중간활동 필수·미완 → 중간활동.
    if midactivity.gate_blocked(store, rec.id):
        guided = next((c for c in chapters if c.mode == "guided"), chapters[-1])
        return guided.idx, "guided", "mid_activity"
    if rec.status == "done":
        last = chapters[-1]
        return last.idx, last.mode, "done"
    # 전·결 읽기: 아직 본문 없는 첫 guided, 없으면 마지막.
    for c in chapters:
        if c.mode == "guided" and c.char_count <= 0:
            return c.idx, "guided", "read"
    last = chapters[-1]
    return last.idx, last.mode, "read"


def list_books(store: Store, user: CurrentUser) -> BooksResponse:
    # 학생은 자기 책만. (교사/관리자 목록은 교사 대시보드 §T2 별도 제공.)
    records = store.list_books_for_student(user.id)
    summaries: list[BookSummary] = []
    for rec in records:
        # chaptersDone = 학생이 진입해 본문이 있는(char_count>0) 챕터 수.
        # 선생성(prefetch)만 된 미진입 챕터는 제외(진척 과대 방지, 학생/06).
        done = sum(
            1 for c in store.list_chapters(rec.id)
            if c.char_count > 0 and not getattr(c, "prefetched", False)
        )
        idx, mode, stage = _resume_for(store, rec)
        summaries.append(
            BookSummary(
                id=rec.id,
                title=rec.title,
                status=rec.status,
                chapters_done=done,
                total_chapters_planned=rec.total_chapters_planned,
                updated_at=rec.updated_at or rec.created_at,
                current_chapter_idx=idx,
                current_chapter_mode=mode,
                current_stage=stage,
            )
        )
    return BooksResponse(books=summaries)


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
            paragraph_count=len(store.list_paragraphs(c.id)),
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


# --- 학생 데이터 열람 (선생님/03, 책 접근자) ---
def _chapter_content(c) -> ChapterContent:
    # 본문은 평문으로 정제해 내보낸다(신규 무영향, 옛 마크다운 데이터도 깨끗히, 이슈2).
    from app.ai.sanitize import sanitize_body

    body = sanitize_body(c.body)
    return ChapterContent(
        idx=c.idx, mode=c.mode, review_status=c.review_status, body=body,
        char_count=len(body), words=c.words,
        illustration_url=c.illustration_path, updated_at=c.created_at,
    )


def list_chapters_content(store: Store, user: CurrentUser, book_id: str) -> ChaptersContentResponse:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)
    return ChaptersContentResponse(
        chapters=[_chapter_content(c) for c in store.list_chapters(book_id)]
    )


def get_chapter_content(store: Store, user: CurrentUser, book_id: str, idx: int) -> ChapterContent:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)
    c = store.get_chapter(book_id, idx)
    if not c:
        raise not_found("챕터를 찾을 수 없습니다.")
    return _chapter_content(c)


def get_plan_messages(store: Store, user: CurrentUser, book_id: str) -> PlanMessagesResponse:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)
    return PlanMessagesResponse(messages=[
        PlanMessageView(role=m.role, content=m.content, created_at=m.created_at)
        for m in store.list_plan_messages(book_id)
    ])


def get_bible_view(store: Store, user: CurrentUser, book_id: str) -> BibleResponse:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)
    rec = store.get_bible(book_id)
    return BibleResponse(bible=rec.data if rec else {})


def list_student_books(
    store: Store, user: CurrentUser, class_id: str, student_id: str
) -> StudentBooksResponse:
    # 담당 교사·admin 만, 해당 학생이 그 학급 소속일 때.
    classroom = store.get_classroom(class_id)
    if not classroom:
        raise not_found("학급을 찾을 수 없습니다.")
    if user.role != "admin" and classroom.teacher_id != user.id:
        raise forbidden("담당 학급이 아닙니다.")
    if not store.is_enrolled(class_id, student_id):
        raise not_found("그 학급의 학생이 아닙니다.")
    summaries: list[BookSummary] = []
    for rec in store.list_books_for_student(student_id):
        if rec.classroom_id != class_id:
            continue
        done = sum(
            1 for c in store.list_chapters(rec.id)
            if c.char_count > 0 and not getattr(c, "prefetched", False)
        )
        summaries.append(BookSummary(
            id=rec.id, title=rec.title, status=rec.status, chapters_done=done,
            total_chapters_planned=rec.total_chapters_planned,
            updated_at=rec.updated_at or rec.created_at,
        ))
    return StudentBooksResponse(books=summaries)


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
def _plan_hash(store: Store, book_id: str) -> str:
    """기획 학생 발화 스냅샷 해시 — 선생성 초안의 최신성(stale) 판정용(학생/04)."""
    msgs = [m.content for m in store.list_plan_messages(book_id) if m.role == "student"]
    digest = hashlib.sha256(" ".join(msgs).encode("utf-8")).hexdigest()[:16]
    return f"{len(msgs)}:{digest}"


async def _run_design(
    store: Store, gemini: GeminiClient, book_id: str, plan_hash: str,
    *, set_writing: bool, label: str,
) -> int:
    """Bible 생성 + 챕터 골격 + RAG 적재(공통). set_writing 이면 book.status='writing'.

    `bible.data['_planHash']` 에 스냅샷 해시를 박아 design 시점에 최신성 판정.
    """
    book = store.get_book(book_id)
    prompt = store.get_prompt(book.prompt_id) if book and book.prompt_id else None
    plan_records = store.list_plan_messages(book_id)
    student_messages = [m.content for m in plan_records if m.role == "student"]
    traits = chat._extract_draft(student_messages).traits
    # Bible 입력에는 학생 답변뿐 아니라 곰(인터뷰어) 질문까지 화자 표기로 보존한다(§01).
    # 무엇을 묻자 무엇을 답했는지 맥락이 살아 인물·배경·분위기 추출 품질이 올라간다.
    plan_dialogue = [
        f"{'학생' if m.role == 'student' else '곰'}: {m.content}" for m in plan_records
    ]

    trace = Trace(store, gemini, gemini.settings, "designer", book_id, gemini.settings.gemini_model_pro)
    bible = await designer.build_bible(gemini, prompt, plan_dialogue, traits)
    bible["_planHash"] = plan_hash
    store.upsert_bible(book_id, bible)
    trace.step(
        "기획·학습목표로 Bible 설계",
        "design_outline",
        {"topic": prompt.topic if prompt else None,
         "objectives": prompt.learning_objectives if prompt else []},
        {"title": bible.get("title"), "characters": len(bible.get("characters", [])),
         "events": len(bible.get("events", []))},
        model=gemini.settings.gemini_model_pro,
        tokens_in=estimate_tokens(" ".join(student_messages)),
        tokens_out=estimate_tokens(str(bible)),
    )

    events = bible.get("events", [])
    total = bible.get("totalChaptersPlanned", len(events) or designer.DEFAULT_TOTAL_CHAPTERS)
    for ev in events:
        idx = ev.get("chapterIdx")
        mode = ev.get("mode", "free")
        if idx and not store.get_chapter(book_id, idx):
            store.create_chapter(book_id, idx, mode)

    # 선생성(prefetch)은 status='planning' 유지(버튼 클릭 시 확정), design 은 'writing' 으로 전이.
    fields: dict = {"title": bible.get("title"), "total_chapters_planned": total}
    if set_writing:
        fields["status"] = "writing"
    store.update_book(book_id, **fields)

    await _index_bible(store, gemini, book_id, bible)
    trace.step("Bible 핵심을 RAG 인덱스에 적재", "embed_store", {"book_id": book_id},
               {"totalChaptersPlanned": total})
    trace.end(status="done", summary=f"'{bible.get('title')}' {label}({total}장)")
    return total


async def design_book(
    store: Store, gemini: GeminiClient, user: CurrentUser, book_id: str
) -> DesignResponse:
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book)

    cur_hash = _plan_hash(store, book_id)
    existing = store.get_bible(book_id)
    # 이미 설계 확정된 책(writing/done)은 멱등 done(재클릭 안전 — 레거시 bible 포함).
    if existing and book.status != "planning":
        return DesignResponse(status="done",
                              total_chapters_planned=existing.data.get("totalChaptersPlanned"))
    # 선생성 초안이 최신이면 Pro 재호출 없이 즉시 확정·진입(학생/04).
    if existing and existing.data.get("_planHash") == cur_hash:
        total = existing.data.get("totalChaptersPlanned")
        store.update_book(book_id, status="writing", title=existing.data.get("title"),
                          total_chapters_planned=total)
        return DesignResponse(status="done", total_chapters_planned=total)

    # 초안 없음/stale → 동기 설계(폴백·정본 경로).
    total = await _run_design(store, gemini, book_id, cur_hash, set_writing=True, label="설계 완료")
    return DesignResponse(status="done", total_chapters_planned=total)


async def prefetch_design(store: Store, gemini: GeminiClient, book_id: str) -> None:
    """기획 대화가 readyToWrite 에 도달하면 Bible 을 백그라운드 선생성(학생/04).

    free 1장 초안은 협업(학생/15)이라 선생성하지 않는다 — Bible 까지만(00 §3 정합).
    멱등·단일성: 같은 해시로 이미 준비됐거나 진행 중이면 skip.
    """
    cur_hash = _plan_hash(store, book_id)
    existing = store.get_bible(book_id)
    if existing and existing.data.get("_planHash") == cur_hash:
        return  # 이미 최신 초안
    if not acquire_prefetch(book_id, "design"):
        return  # 진행 중(단일성)
    try:
        await _run_design(store, gemini, book_id, cur_hash, set_writing=False, label="선생성(prefetch)")
    except Exception:
        pass  # 실패해도 학생 흐름 불변(버튼 클릭 시 동기 폴백)
    finally:
        release_prefetch(book_id, "design")


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
