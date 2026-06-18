"""다음 장 백그라운드 선생성(학생/06) — prefetch 저장·진척 제외·진입 시 즉시 재생·락·폴백."""
from __future__ import annotations

import json

from app.ai.gemini import GeminiClient
from app.config import get_settings
from app.services import chapters
from app.services.prefetch import acquire_prefetch, is_inflight, release_prefetch
from app.store import get_store
from tests.conftest import auth


async def _designed_book(client, email="kid_pf@test"):
    th = auth("teacher_pf@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(
        f"/classes/{class_id}/prompts", headers=th,
        json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}},
    )
    sh = auth(email, "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    return sh, book_id


def _gem():
    return GeminiClient(get_settings())


async def _read_sse(client, url, headers):
    events = []
    async with client.stream("GET", url, headers=headers) as resp:
        event = None
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                events.append((event, json.loads(line.split(":", 1)[1].strip())))
    return events


# --- 단일성 락 ---

def test_prefetch_lock_single_flight():
    assert acquire_prefetch("b1", 4) is True
    assert acquire_prefetch("b1", 4) is False   # 진행 중 → skip
    assert is_inflight("b1", 4) is True
    release_prefetch("b1", 4)
    assert acquire_prefetch("b1", 4) is True     # 해제 후 다시 가능
    release_prefetch("b1", 4)


# --- guided 선생성 + 진척 제외 ---

async def test_prefetch_saves_body_but_excluded_from_progress(client):
    sh, book_id = await _designed_book(client)
    store = get_store()

    await chapters.prefetch_chapter(store, _gem(), book_id, 4)  # guided 장
    ch4 = store.get_chapter(book_id, 4)
    assert ch4 is not None and ch4.char_count > 0  # 본문 저장됨
    assert ch4.prefetched is True

    # 본문이 있어도 미진입(prefetched) 이라 chaptersDone 에 안 잡힌다.
    books = (await client.get("/books", headers=sh)).json()["books"]
    mine = next(b for b in books if b["id"] == book_id)
    assert mine["chaptersDone"] == 0


async def test_entering_prefetched_chapter_is_instant_and_counts(client):
    sh, book_id = await _designed_book(client, email="kid_pf2@test")
    store = get_store()
    await chapters.prefetch_chapter(store, _gem(), book_id, 4)
    saved = store.get_chapter(book_id, 4).body

    events = await _read_sse(client, f"/books/{book_id}/chapters/4/stream", sh)
    body = "".join(e[1]["text"] for e in events if e[0] == "token")
    assert body == saved                                  # 저장본 그대로(새 생성 없음)

    ch4 = store.get_chapter(book_id, 4)
    assert ch4.prefetched is False                        # 진입 → 표식 해제
    books = (await client.get("/books", headers=sh)).json()["books"]
    mine = next(b for b in books if b["id"] == book_id)
    assert mine["chaptersDone"] == 1


# --- free 챕터는 선생성 안 함(협업, 학생/15) ---

async def test_prefetch_skips_free_chapter(client):
    sh, book_id = await _designed_book(client, email="kid_pf3@test")
    store = get_store()
    await chapters.prefetch_chapter(store, _gem(), book_id, 1)  # idx1 = free
    ch1 = store.get_chapter(book_id, 1)
    assert ch1 is None or ch1.char_count == 0  # 본문 생성 안 함


# --- 마지막 장: prefetch 는 done 으로 안 올림, 진입 시 완독 처리 ---

async def test_prefetch_final_does_not_complete_until_entered(client):
    sh, book_id = await _designed_book(client, email="kid_pf4@test")
    store = get_store()
    total = store.get_bible(book_id).data["totalChaptersPlanned"]

    await chapters.prefetch_chapter(store, _gem(), book_id, total)
    assert store.get_book(book_id).status != "done"        # 미진입 → 미완독

    await _read_sse(client, f"/books/{book_id}/chapters/{total}/stream", sh)
    assert store.get_book(book_id).status == "done"        # 진입 → 완독
    finished = store.list_events(book_id=book_id, type="book_finished")
    assert len(finished) >= 1


# --- 트리거: 현재 장 done 후 다음 장 선생성 ---

async def test_stream_triggers_next_chapter_prefetch(client):
    sh, book_id = await _designed_book(client, email="kid_pf5@test")
    store = get_store()
    # ch4(guided) 스트림 → 백그라운드로 ch5 선생성.
    await _read_sse(client, f"/books/{book_id}/chapters/4/stream", sh)
    ch5 = store.get_chapter(book_id, 5)
    assert ch5 is not None and ch5.char_count > 0 and ch5.prefetched is True
