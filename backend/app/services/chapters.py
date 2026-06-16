"""챕터 집필 SSE 오케스트레이션 — 03-기능명세서 §5. FR-S4/S5/S7.

이벤트 순서: meta → (guided: illustration, prompt) → token* → done.
오류 시 error 이벤트. 15초마다 `: ping` 하트비트.
재연결: ?from=<charOffset> 로 이어받기.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from app.ai import imagen, rag, writer
from app.ai.gemini import GeminiClient
from app.deps import CurrentUser
from app.services.books import assert_can_access_book, get_book_or_404
from app.store.base import Store

HEARTBEAT_SECS = 15.0


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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

        # 1) meta (최초 1회)
        await queue.put(_sse("meta", {"chapterIdx": idx, "mode": mode, "totalChaptersPlanned": total}))

        # 2) guided 모드: 삽화 선노출 + 능동 질문 (FR-S5)
        if mode == "guided":
            url, alt = await imagen.generate_illustration(
                gemini, book_id, idx, event.get("summary", ""), bible.get("characters", [])
            )
            store.update_chapter(chapter.id, illustration_path=url)
            await queue.put(_sse("illustration", {"url": url, "alt": alt}))
            await queue.put(_sse("prompt", {"text": "이 그림 속에서는 무슨 일이 벌어지고 있을까요?"}))

        # 3) 본문 토큰 (RAG 컨텍스트 고정)
        context = await rag.retrieve_context(
            store, gemini, book_id, event.get("summary", ""), k=5
        )
        body = ""
        running = 0
        async for chunk in writer.stream_chapter(gemini, bible, event, context):
            body += chunk
            # 재연결 이어받기: from_offset 이전은 건너뛴다.
            if running + len(chunk) <= from_offset:
                running += len(chunk)
                continue
            emit = chunk
            if running < from_offset:
                emit = chunk[from_offset - running :]
            running += len(chunk)
            await queue.put(_sse("token", {"text": emit}))

        # 4) 저장 + RAG 적재 + done
        words = writer.select_words(body)
        store.update_chapter(
            chapter.id, body=body, char_count=len(body), words=words, review_status="pending"
        )
        await rag.index_text(store, gemini, book_id, chapter.id, body)

        next_available = bool(total and idx < total)
        if not next_available:
            store.update_book(book_id, status="done")

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
