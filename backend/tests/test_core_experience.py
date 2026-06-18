"""핵심경험(05) — 완독 안정·offset 통일·결말 payoff 테스트."""
from __future__ import annotations

import json

from app.services.chapters import _u16_len
from tests.conftest import auth


def test_u16_len_matches_js_length():
    assert _u16_len("가나다") == 3  # 한글(BMP) = 코드포인트와 동일
    assert _u16_len("ab") == 2
    assert _u16_len("🎉") == 2  # 비BMP 이모지 = JS .length 2 와 일치
    assert _u16_len("별이🎉") == 4


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


async def _setup_book(client):
    th = auth("teacher@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(
        f"/classes/{class_id}/prompts", headers=th,
        json={"topic": "물", "learningObjectives": ["증발"], "assessment": {}},
    )
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth("kid_core@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    return sh, book_id


async def test_final_chapter_payoff_and_completion(client):
    from app.store import get_store

    sh, book_id = await _setup_book(client)
    total = (await client.get(f"/books/{book_id}", headers=sh)).json()["totalChaptersPlanned"]

    # 마지막 장 스트림
    events = await _read_sse(client, f"/books/{book_id}/chapters/{total}/stream", sh)
    done = next(e[1] for e in events if e[0] == "done")
    body = "".join(e[1]["text"] for e in events if e[0] == "token")

    assert done["nextChapterAvailable"] is False  # 마지막 장 → 다음 없음
    assert "끝" in body  # mock 결말 회수 텍스트
    # 완독 처리: book status done + book_finished 이벤트(서버 파생)
    store = get_store()
    assert store.get_book(book_id).status == "done"
    finished = store.list_events(book_id=book_id, type="book_finished")
    assert len(finished) >= 1


async def test_nonfinal_chapter_next_available(client):
    sh, book_id = await _setup_book(client)
    events = await _read_sse(client, f"/books/{book_id}/chapters/1/stream", sh)
    done = next(e[1] for e in events if e[0] == "done")
    assert done["nextChapterAvailable"] is True  # 본문 있음 + 마지막 아님


async def test_resume_offset_utf16(client):
    # ?from= 으로 이어받기: 받은 charCount 이후만 전송(UTF-16 단위 일치).
    sh, book_id = await _setup_book(client)
    full = await _read_sse(client, f"/books/{book_id}/chapters/1/stream", sh)
    full_body = "".join(e[1]["text"] for e in full if e[0] == "token")
    cut = _u16_len(full_body) // 2
    resumed = await _read_sse(client, f"/books/{book_id}/chapters/1/stream?from={cut}", sh)
    resumed_body = "".join(e[1]["text"] for e in resumed if e[0] == "token")
    # 이어받은 본문 = 전체에서 cut(UTF-16) 이후
    assert _u16_len(resumed_body) == _u16_len(full_body) - cut
