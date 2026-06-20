"""자유집필 협업 서비스 — 한 마디 → 한 문단 생성 또는 지도(학생/15 §2).

free(기·승) 챕터에서만 유효. 좌(문단)·우(대화 턴)를 누적하고 chapters.body 를 재조립해
독서/RAG/학습이 기존 통짜 body 경로를 그대로 쓰게 한다(독서 경험 불변).
"""
from __future__ import annotations

from app.ai import chat, rag, safety, writer
from app.ai.gemini import GeminiClient
from app.ai.safety import check_input
from app.ai.sanitize import sanitize_body
from app.ai.trace import Trace
from app.deps import CurrentUser
from app.errors import conflict, not_found
from app.models.schemas import (
    CollabCoaching,
    CollabParagraph,
    CollabParagraphView,
    CollabReply,
    CollabState,
    CollabTurnView,
    ParagraphEditResult,
    ParagraphReorderResult,
)
from app.services.books import (
    assert_can_access_book,
    assert_owner_student,
    get_book_or_404,
)
from app.store.base import Store

# 기·승 free 챕터가 이 문단 수에 도달하면 협업 완료(→ 중간활동/다음 단계 게이트).
COLLAB_TARGET_PARAGRAPHS = 4


def _event_for(store: Store, book_id: str, idx: int) -> dict | None:
    rec = store.get_bible(book_id)
    if not rec:
        return None
    return next((e for e in rec.data.get("events", []) if e.get("chapterIdx") == idx), None)


def _require_free_chapter(store: Store, book_id: str, idx: int):
    """협업 대상 free 챕터 보장. 설계 전이거나 guided 면 거부."""
    event = _event_for(store, book_id, idx)
    if event is None:
        raise conflict("먼저 설계(design)가 필요합니다.")
    if event.get("mode", "free") != "free":
        raise conflict("이 챕터는 협업 대상이 아닙니다(유도 모드).")
    chapter = store.get_chapter(book_id, idx) or store.create_chapter(book_id, idx, "free")
    return chapter, event


async def collab_turn(
    store: Store, gemini: GeminiClient, user: CurrentUser, book_id: str, idx: int,
    message: str, accept: bool,
) -> CollabReply:
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book)
    chapter, event = _require_free_chapter(store, book_id, idx)

    # 1) 입력 안전 게이트(기획/revise 와 동일 규약).
    safe = check_input(message)
    if safe.risk:
        store.add_safety_flag(book_id, user.id, "collab", "정서 위험 신호 감지")
    if not safe.ok:
        store.add_writing_turn(chapter.id, book_id, "student", "message", message)
        return CollabReply(kind="error", message=safe.suggestion or "그건 선생님과 함께 이야기해보자.")

    # 2) 학생 턴 저장.
    store.add_writing_turn(chapter.id, book_id, "student", "message", message)

    paragraphs = store.list_paragraphs(chapter.id)
    prev_body = paragraphs[-1].body if paragraphs else ""
    objective = event.get("objective")

    trace = Trace(store, gemini, gemini.settings, "writer", book_id, gemini.settings.gemini_model_flash)

    # 2.5) 대화 수정 의도("N번째 문단 고쳐줘") → 새 문단 append 가 아니라 대상 문단 교체(§02).
    if not accept:
        target = chat.detect_edit_target(message, len(paragraphs))
        if target is not None:
            return await _revise_paragraph_turn(
                store, gemini, book_id, chapter, event, paragraphs, target, message, trace
            )

    # 3) 흐름/주제 점검(accept 면 제안 수용 → 바로 생성).
    if not accept:
        decision = await chat.assess_flow(gemini, store.get_bible(book_id).data, prev_body, objective, message)
        if decision.get("action") == "coach":
            text = decision.get("suggestion") or chat._coach_text(decision.get("reasons", []), objective)
            store.add_writing_turn(chapter.id, book_id, "writer", "coaching", text)
            trace.step("의도 점검(지도)", "assess_flow", {"intent": message[:80]},
                       {"action": "coach", "reasons": decision.get("reasons", [])})
            trace.end(status="done", summary=f"{idx}장 협업 지도")
            return CollabReply(
                kind="coaching",
                coaching=CollabCoaching(text=text, reasons=decision.get("reasons", [])),
                chapter_complete=False,
            )

    # 4) 문단 생성.
    bible = store.get_bible(book_id).data
    context = await rag.retrieve_context(store, gemini, book_id, message, k=5)
    raw = await writer.write_paragraph(
        gemini, bible, event, [p.body for p in paragraphs], message, context
    )
    body = sanitize_body(raw)  # 본문 정제(학생/08)
    if not body:
        trace.end(status="error", error="empty_paragraph")
        return CollabReply(kind="error", message="문단을 만들지 못했어. 다시 한 번 말해줄래?")

    # 출력 안전(무거운 장면 신호만 교사용 기록, 학생 흐름 비차단).
    try:
        from app.services.policy import resolve_safety_level

        out = safety.filter_output(body, safety_level=resolve_safety_level(store, book_id))
        if out.flags:
            store.add_safety_flag(book_id, user.id, "output", f"무거운 장면 신호: {', '.join(out.flags)}",
                                  category="heavy_scene")
    except Exception:
        pass

    seq = len(paragraphs) + 1
    para = store.add_paragraph(chapter.id, book_id, seq, body, source="collab")
    store.add_writing_turn(chapter.id, book_id, "writer", "message", body, paragraph_id=para.id)

    # 5) chapters.body 재조립(독서/RAG/학습 하위호환) + 낱말·진척 갱신.
    full = _resync_chapter(store, book_id, chapter, bible)
    store.update_book(book_id)  # 마지막 활동 시각

    complete = seq >= COLLAB_TARGET_PARAGRAPHS
    question = None
    if not complete:
        question = await chat.next_paragraph_question(
            gemini, bible, [p.body for p in paragraphs] + [body], event
        )
        store.add_writing_turn(chapter.id, book_id, "writer", "question", question)
    else:
        await rag.index_text(store, gemini, book_id, chapter.id, full)  # 완료 시 1회 인덱스

    trace.step("문단 생성", "write_paragraph", {"seq": seq, "intent": message[:80]},
               {"chars": len(body), "chapterComplete": complete})
    trace.end(status="done", summary=f"{idx}장 협업 {seq}문단")
    return CollabReply(
        kind="paragraph",
        paragraph=CollabParagraph(seq=seq, body=body),
        question=question,
        chapter_complete=complete,
    )


def collab_state(store: Store, user: CurrentUser, book_id: str, idx: int) -> CollabState:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)
    chapter = store.get_chapter(book_id, idx)
    if not chapter:
        raise not_found("챕터를 찾을 수 없습니다.")
    paragraphs = store.list_paragraphs(chapter.id)
    turns = store.list_writing_turns(chapter.id)
    return CollabState(
        paragraphs=[CollabParagraphView(seq=p.seq, body=p.body, source=p.source) for p in paragraphs],
        turns=[CollabTurnView(role=t.role, kind=t.kind, content=t.content, created_at=t.created_at)
               for t in turns],
        chapter_complete=len(paragraphs) >= COLLAB_TARGET_PARAGRAPHS,
    )


def _rebuild_body(store: Store, chapter_id: str) -> str:
    """문단을 seq 순서로 이어 chapters.body 캐시 재조립."""
    return "\n\n".join(p.body for p in store.list_paragraphs(chapter_id))


def _resync_chapter(store: Store, book_id: str, chapter, bible: dict) -> str:
    """문단 변경(생성/교체/순서변경) 후 chapters.body·낱말·검수상태를 재동기화."""
    full = _rebuild_body(store, chapter.id)
    grade = _student_grade(store, book_id)
    names = [c.get("name", "") for c in bible.get("characters", []) if c.get("name")]
    store.update_chapter(
        chapter.id, body=full, char_count=len(full),
        words=writer.select_words(full, grade, names), review_status="pending",
    )
    return full


async def _revise_paragraph_turn(
    store: Store, gemini: GeminiClient, book_id: str, chapter, event: dict,
    paragraphs: list, target_seq: int, message: str, trace: Trace,
) -> CollabReply:
    """대화 수정("N번째 문단 고쳐줘") — 대상 문단을 교체(append 아님, §02)."""
    bible = store.get_bible(book_id).data
    current = next((p for p in paragraphs if p.seq == target_seq), None)
    if current is None:
        trace.end(status="error", error="edit_target_not_found")
        return CollabReply(kind="error", message="고칠 문단을 찾지 못했어. 몇 번째 문단인지 다시 알려줄래?")

    directive = await chat.interpret_revision(gemini, message)
    context = await rag.retrieve_context(store, gemini, book_id, current.body, k=5)
    raw = await writer.revise_paragraph(gemini, bible, event, current.body, directive, context)
    body = sanitize_body(raw)
    if not body:
        trace.end(status="error", error="empty_revision")
        return CollabReply(kind="error", message="문단을 고치지 못했어. 다시 한 번 말해줄래?")

    store.update_paragraph(chapter.id, target_seq, body, source="revise")
    store.add_writing_turn(chapter.id, book_id, "writer", "message", body)
    full = _resync_chapter(store, book_id, chapter, bible)
    store.update_book(book_id)
    await rag.index_text(store, gemini, book_id, chapter.id, full)

    trace.step("문단 수정(교체)", "revise_paragraph", {"seq": target_seq, "intent": message[:80]},
               {"chars": len(body)})
    trace.end(status="done", summary=f"{chapter.idx}장 {target_seq}문단 교체")
    return CollabReply(
        kind="paragraph",
        paragraph=CollabParagraph(seq=target_seq, body=body),
        replaced_seq=target_seq,
        chapter_complete=len(paragraphs) >= COLLAB_TARGET_PARAGRAPHS,
    )


async def edit_paragraph(
    store: Store, gemini: GeminiClient, user: CurrentUser, book_id: str, idx: int,
    seq: int, body: str,
) -> ParagraphEditResult:
    """학생 직접편집(수정버튼) — 본문 교체 + 정제·안전 재검 + 과편집 시 곰 작가 대안(§02)."""
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book)
    chapter, event = _require_free_chapter(store, book_id, idx)
    paragraphs = store.list_paragraphs(chapter.id)
    target = next((p for p in paragraphs if p.seq == seq), None)
    if target is None:
        raise not_found("문단을 찾을 수 없습니다.")

    clean = sanitize_body(body)
    if not clean:
        raise conflict("문단 내용이 비어 있습니다.")

    # 입력 안전 게이트(학생 직접 작성).
    safe = check_input(clean)
    if safe.risk:
        store.add_safety_flag(book_id, user.id, "collab", "정서 위험 신호 감지(직접편집)")
    if not safe.ok:
        raise conflict(safe.suggestion or "그 내용은 선생님과 함께 이야기해보자.")

    bible_rec = store.get_bible(book_id)
    bible = bible_rec.data if bible_rec else {}
    store.update_paragraph(chapter.id, seq, clean, source="revise")
    # 직접편집을 AI 컨텍스트에 동기화(대화 로그에 학생 편집 턴 적재).
    store.add_writing_turn(chapter.id, book_id, "student", "message", f"[{seq}번 문단 직접수정] {clean}")
    full = _resync_chapter(store, book_id, chapter, bible)
    store.update_book(book_id)
    await rag.index_text(store, gemini, book_id, chapter.id, full)

    # 과도하게 이상한 편집이면 곰 작가가 대안 제안(차단 아님).
    prev_body = next((p.body for p in paragraphs if p.seq == seq - 1), "")
    next_body = next((p.body for p in paragraphs if p.seq == seq + 1), "")
    verdict = await chat.assess_edit(
        gemini, bible, prev_body, next_body, clean, event.get("objective")
    )
    suggestion = verdict.get("suggestion") if verdict.get("weird") else None
    if suggestion:
        store.add_writing_turn(chapter.id, book_id, "writer", "coaching", suggestion)
    return ParagraphEditResult(paragraph=CollabParagraph(seq=seq, body=clean), suggestion=suggestion)


def reorder_paragraphs(
    store: Store, user: CurrentUser, book_id: str, idx: int, order: list[int],
) -> ParagraphReorderResult:
    """드래그 순서변경 — order(현재 seq 순열)대로 재정렬(§02)."""
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book)
    chapter, _ = _require_free_chapter(store, book_id, idx)
    paragraphs = store.list_paragraphs(chapter.id)
    by_seq = {p.seq: p for p in paragraphs}
    if sorted(order) != sorted(by_seq.keys()):
        raise conflict("문단 순서 목록이 현재 문단과 맞지 않습니다.")

    ordered_ids = [by_seq[s].id for s in order]
    store.reorder_paragraphs(chapter.id, ordered_ids)
    bible = store.get_bible(book_id)
    _resync_chapter(store, book_id, chapter, bible.data if bible else {})
    store.add_writing_turn(chapter.id, book_id, "student", "message", "[문단 순서 변경]")
    store.update_book(book_id)
    updated = store.list_paragraphs(chapter.id)
    return ParagraphReorderResult(
        paragraphs=[CollabParagraphView(seq=p.seq, body=p.body, source=p.source) for p in updated]
    )


def _student_grade(store: Store, book_id: str) -> int | None:
    try:
        book = store.get_book(book_id)
        prof = store.get_profile(book.student_id) if book and book.student_id else None
        return prof.grade if prof else None
    except Exception:
        return None
