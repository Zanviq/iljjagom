"""guided(자동생성) 장이 지속 stall 할 때 완독이 막히지 않아야 한다(이슈a 확장).

재현: 실 Gemini 생성이 stall → 60s 타임아웃 → body 비었을 때, 결말이 아닌 guided
중간 장은 현재 `raise` 라서 학생이 영영 진행 불가(매 재시도 재수집). guided 장은
결말이든 중간이든 폴백 본문으로 완독 보장돼야 한다.
"""
from __future__ import annotations

import asyncio
import json

import app.ai.writer as writer
import app.services.chapters as chapters
from app.ai.gemini import GeminiClient
from app.store import get_store


def _setup_book(total: int = 6) -> tuple[object, GeminiClient, str]:
    store = get_store()
    book = store.create_book("kid-stall", None, None)
    events = []
    for i in range(1, total + 1):
        events.append({
            "chapterIdx": i,
            "mode": "free" if i <= total // 2 else "guided",
            "objective": "증발",
            "summary": f"{i}장 개요",
        })
    store.upsert_bible(book.id, {
        "title": "물 이야기",
        "totalChaptersPlanned": total,
        "characters": [{"name": "토끼"}],
        "world": {"setting": "숲", "tone": "따뜻한"},
        "events": events,
        "secretArc": {"hidden": True, "outline": "모두가 성장했어요"},
    })
    return store, GeminiClient(), book.id


async def _drain(store, gemini, book_id, idx) -> list[tuple[str, dict]]:
    queue: asyncio.Queue = asyncio.Queue()
    await chapters._produce(queue, store, gemini, book_id, idx, 0)
    out = []
    while True:
        item = await queue.get()
        if item is None:
            break
        # "event: X\ndata: {...}\n\n" 파싱
        ev = None
        for line in item.splitlines():
            if line.startswith("event:"):
                ev = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                out.append((ev, json.loads(line.split(":", 1)[1].strip())))
    return out


async def test_guided_final_chapter_falls_back_on_stall(monkeypatch):
    """결말 guided 장: 생성 stall → 폴백 본문으로 done(완독 보장)."""
    store, gemini, book_id = _setup_book(total=6)

    async def _stall(*a, **k):
        await asyncio.sleep(1.0)  # 타임아웃보다 길게
        yield "never"

    monkeypatch.setattr(writer, "stream_chapter", _stall)
    monkeypatch.setattr(chapters, "LIVE_GEN_TIMEOUT", 0.05)

    events = await _drain(store, gemini, book_id, 6)
    kinds = [e for e, _ in events]
    assert "error" not in kinds, f"결말 장이 폴백 없이 에러로 끝남: {events}"
    done = next(d for e, d in events if e == "done")
    assert done["charCount"] > 0
    # 저장되어 재진입 시 즉시 served_stored 로 떠야 한다(매번 재수집 방지).
    ch = store.get_chapter(book_id, 6)
    assert ch.body and ch.char_count > 0


async def test_guided_middle_chapter_falls_back_on_stall(monkeypatch):
    """중간 guided 장(비-결말): 생성 stall 이 지속되면 영구 블록 방지 위해 폴백."""
    store, gemini, book_id = _setup_book(total=6)  # 4장 = 중간 guided

    async def _stall(*a, **k):
        await asyncio.sleep(1.0)
        yield "never"

    monkeypatch.setattr(writer, "stream_chapter", _stall)
    monkeypatch.setattr(chapters, "LIVE_GEN_TIMEOUT", 0.05)

    events = await _drain(store, gemini, book_id, 4)
    kinds = [e for e, _ in events]
    assert "error" not in kinds, f"중간 guided 장이 폴백 없이 에러로 끝남(영구 블록): {events}"
    done = next(d for e, d in events if e == "done")
    assert done["charCount"] > 0
    assert done["nextChapterAvailable"] is True  # 다음 장 진행 가능해야
    ch = store.get_chapter(book_id, 4)
    assert ch.body and ch.char_count > 0
