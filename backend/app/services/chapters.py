"""챕터 집필 SSE 오케스트레이션 — 03-기능명세서 §5. FR-S4/S5/S7.

이벤트 순서: meta → (guided: illustration, prompt) → token* → done.
오류 시 error 이벤트. 15초마다 `: ping` 하트비트.
재연결: ?from=<charOffset> 로 이어받기.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from app.ai import chat, editor, imagen, rag, writer
from app.ai.gemini import GeminiClient
from app.ai.skills.base import estimate_tokens
from app.ai.trace import Trace
from app.deps import CurrentUser
from app.services.books import assert_can_access_book, get_book_or_404
from app.store.base import Store

HEARTBEAT_SECS = 15.0


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _emit_token(queue: asyncio.Queue, chunk: str, running: int, from_offset: int) -> int:
    """from_offset(이미 받은 글자 수) 이후만 token 으로 보낸다. 갱신된 running 반환."""
    new_running = running + len(chunk)
    if new_running <= from_offset:
        return new_running
    emit = chunk[from_offset - running :] if running < from_offset else chunk
    await queue.put(_sse("token", {"text": emit}))
    return new_running


def _find_event(bible: dict, idx: int) -> dict | None:
    return next((e for e in bible.get("events", []) if e.get("chapterIdx") == idx), None)


async def _produce(
    queue: asyncio.Queue,
    store: Store,
    gemini: GeminiClient,
    book_id: str,
    idx: int,
    from_offset: int,
) -> None:
    """SSE 문자열을 큐에 적재. 완료/오류 시 None(sentinel) 을 넣는다."""
    try:
        book = store.get_book(book_id)
        bible_rec = store.get_bible(book_id)
        if not book or not bible_rec:
            await queue.put(
                _sse("error", {"code": "conflict", "message": "먼저 설계(design)가 필요합니다.", "retryable": False})
            )
            return

        bible = bible_rec.data
        total = bible.get("totalChaptersPlanned")
        events = bible.get("events", [])
        event = next((e for e in events if e.get("chapterIdx") == idx), None)
        if event is None:
            await queue.put(
                _sse("error", {"code": "not_found", "message": "해당 챕터가 없습니다.", "retryable": False})
            )
            return

        chapter = store.get_chapter(book_id, idx) or store.create_chapter(
            book_id, idx, event.get("mode", "free")
        )
        mode = chapter.mode
        # 이미 집필된 챕터는 저장본을 그대로 흘린다(재구독·수정/편집 반영). 첫 집필만 생성.
        served_stored = bool(chapter.body) and chapter.char_count > 0

        # 1) meta (최초 1회)
        await queue.put(_sse("meta", {"chapterIdx": idx, "mode": mode, "totalChaptersPlanned": total}))

        # 2) guided 모드: 삽화 선노출 + 능동 질문 (FR-S5). 재구독 시 저장된 삽화 재사용.
        if mode == "guided":
            if chapter.illustration_path:
                url, alt = chapter.illustration_path, "이 장면의 삽화"
            else:
                url, alt = await imagen.generate_illustration(
                    gemini, book_id, idx, event.get("summary", ""), bible.get("characters", [])
                )
                store.update_chapter(chapter.id, illustration_path=url)
            await queue.put(_sse("illustration", {"url": url, "alt": alt}))
            await queue.put(_sse("prompt", {"text": "이 그림 속에서는 무슨 일이 벌어지고 있을까요?"}))

        # 3) 본문 토큰
        running = 0
        if served_stored:
            body = chapter.body
            for i in range(0, len(body), 4):
                await asyncio.sleep(0)  # 이벤트 루프 양보(하트비트/취소 반영)
                running = await _emit_token(queue, body[i : i + 4], running, from_offset)
            words = chapter.words
        else:
            # 첫 집필: RAG 컨텍스트 고정 + 생성 + 저장 + 적재.
            context = await rag.retrieve_context(
                store, gemini, book_id, event.get("summary", ""), k=5
            )
            body = ""
            async for chunk in writer.stream_chapter(gemini, bible, event, context):
                body += chunk
                running = await _emit_token(queue, chunk, running, from_offset)
            words = writer.select_words(body)
            store.update_chapter(
                chapter.id, body=body, char_count=len(body), words=words, review_status="pending"
            )
            await rag.index_text(store, gemini, book_id, chapter.id, body)
            next_available = bool(total and idx < total)
            if not next_available:
                store.update_book(book_id, status="done")
            else:
                store.update_book(book_id)  # 집필 완료 → 마지막 활동 시각 갱신(이어 읽기 정렬)

        # 4) done
        next_available = bool(total and idx < total)
        await queue.put(
            _sse(
                "done",
                {
                    "chapterIdx": idx,
                    "words": words,
                    "nextChapterAvailable": next_available,
                    "charCount": len(body),
                },
            )
        )
    except Exception:
        await queue.put(
            _sse("error", {"code": "ai_unavailable", "message": "본문 생성 중 오류가 발생했어요.", "retryable": True})
        )
    finally:
        await queue.put(None)


async def stream_chapter(
    store: Store,
    gemini: GeminiClient,
    user: CurrentUser,
    book_id: str,
    idx: int,
    from_offset: int = 0,
) -> AsyncIterator[str]:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)

    queue: asyncio.Queue = asyncio.Queue()
    producer = asyncio.create_task(
        _produce(queue, store, gemini, book_id, idx, from_offset)
    )
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECS)
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # 하트비트
                continue
            if item is None:
                break
            yield item
    finally:
        producer.cancel()


# --- Tier3 편집 검수 (P2-3, 비동기) ---
async def run_first_draft_review(
    store: Store, gemini: GeminiClient, book_id: str, idx: int
) -> None:
    """챕터 초고 직후 BackgroundTask 로 호출. review_status=pending 인 챕터만 검수한다.

    학생에게 대기로 노출되지 않는다(스트림 종료 후 백그라운드). 멱등(이미 검수된 챕터는 무시).
    """
    chapter = store.get_chapter(book_id, idx)
    if not chapter or chapter.review_status != "pending" or not chapter.body:
        return
    bible_rec = store.get_bible(book_id)
    if not bible_rec:
        return
    event = _find_event(bible_rec.data, idx) or {}
    trace = Trace(store, gemini, gemini.settings, "editor", book_id, gemini.settings.gemini_model_flash)
    objective = (event.get("objective") or "").strip()
    trace.step(
        "학습목표 도달도 점검",
        "verify_objective",
        {"objective": objective},
        {"met": bool(objective and objective in chapter.body)},
    )
    try:
        result = await editor.review_chapter(gemini, bible_rec.data, event, chapter.body)
    except Exception:
        # 편집 실패는 학생 흐름을 막지 않는다(초고 유지, 다음 기회에 재검수 가능).
        trace.end(status="error", error="editor_failed")
        store.update_chapter(chapter.id, review_status="ok")
        return
    trace.step(
        "초고 검수·다듬기",
        "generate_text",
        {"role": "editor", "chapterIdx": idx},
        {"changed": result.body != chapter.body, "reviewStatus": result.review_status, "notes": result.notes},
        model=gemini.settings.gemini_model_flash,
        tokens_in=estimate_tokens(chapter.body),
        tokens_out=estimate_tokens(result.body),
    )
    trace.end(status="done", summary=f"{idx}장 검수 완료")
    if result.body != chapter.body:
        await rag.index_text(store, gemini, book_id, chapter.id, result.body)
        store.update_chapter(
            chapter.id,
            body=result.body,
            char_count=len(result.body),
            words=writer.select_words(result.body),
            review_status=result.review_status,
        )
    else:
        store.update_chapter(chapter.id, review_status=result.review_status)


# --- 자유모드 수정요청 파이프라인 (P2-2, 비동기) ---
async def run_revise(
    store: Store, gemini: GeminiClient, book_id: str, idx: int, instruction: str
) -> None:
    """대화 AI(요청 해석) → 집필 AI(재생성) → 편집 검수 → 반영. BackgroundTask 로 호출."""
    chapter = store.get_chapter(book_id, idx)
    if not chapter or not chapter.body:
        return
    bible_rec = store.get_bible(book_id)
    if not bible_rec:
        return
    bible = bible_rec.data
    event = _find_event(bible, idx) or {}

    store.update_chapter(chapter.id, review_status="revising")
    trace = Trace(store, gemini, gemini.settings, "writer", book_id, gemini.settings.gemini_model_flash)
    try:
        directive = await chat.interpret_revision(gemini, instruction)
        trace.step("수정 요청 해석", "tutor_answer", {"instruction": instruction}, {"directive": directive},
                   model=gemini.settings.gemini_model_flash_lite,
                   tokens_in=estimate_tokens(instruction), tokens_out=estimate_tokens(directive))
        context = await rag.retrieve_context(
            store, gemini, book_id, event.get("summary", ""), k=5
        )
        trace.step("관련 설정 인출", "retrieve_context", {"query": event.get("summary", ""), "k": 5},
                   {"chars": len(context)})
        revised = await writer.revise_text(
            gemini, bible, event, context, chapter.body, directive
        )
        trace.step("요청 반영해 재집필", "generate_text", {"role": "writer", "chapterIdx": idx},
                   {"chars": len(revised)}, model=gemini.settings.gemini_model_flash,
                   tokens_in=estimate_tokens(chapter.body), tokens_out=estimate_tokens(revised))
        result = await editor.review_chapter(gemini, bible, event, revised)
        trace.step("수정본 검수", "generate_text", {"role": "editor"},
                   {"reviewStatus": result.review_status}, model=gemini.settings.gemini_model_flash,
                   tokens_in=estimate_tokens(revised), tokens_out=estimate_tokens(result.body))
    except Exception:
        # 실패 시 원본 유지 + 상태 복구.
        trace.end(status="error", error="revise_failed")
        store.update_chapter(chapter.id, review_status="ok")
        return

    trace.end(status="done", summary=f"{idx}장 수정 반영")
    await rag.index_text(store, gemini, book_id, chapter.id, result.body)
    store.update_chapter(
        chapter.id,
        body=result.body,
        char_count=len(result.body),
        words=writer.select_words(result.body),
        review_status=result.review_status,
    )
    store.update_book(book_id)  # 마지막 활동 시각 갱신(이어 읽기 정렬)
