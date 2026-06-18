"""중간활동 게이트(학생/15 §3) — 기·승 완료→필수 중간활동→전·결 prefetch·게이트 해제."""
from __future__ import annotations

import json

from app.services.collab import COLLAB_TARGET_PARAGRAPHS
from app.store import get_store
from tests.conftest import auth

FREE_CHAPTERS = (1, 2, 3)  # designer mock: 앞 절반 free, 뒤 절반 guided


async def _designed_book(client, email="kid_mid@test"):
    th = auth("teacher_mid@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth(email, "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    return sh, book_id


async def _finish_giseung(client, sh, book_id):
    """모든 free 챕터를 목표 문단까지 협업 완료."""
    for idx in FREE_CHAPTERS:
        for i in range(COLLAB_TARGET_PARAGRAPHS):
            await client.post(f"/books/{book_id}/chapters/{idx}/collab", headers=sh,
                              json={"message": f"토끼가 {i}번째 걸음을 걸었어"})


async def _read_sse(client, url, headers):
    events = []
    async with client.stream("GET", url, headers=headers) as resp:
        ev = None
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                ev = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                events.append((ev, json.loads(line.split(":", 1)[1].strip())))
    return events


async def test_mid_activity_not_required_before_giseung(client):
    sh, book_id = await _designed_book(client)
    ma = (await client.get(f"/books/{book_id}/mid-activity", headers=sh)).json()
    assert ma["required"] is False and ma["done"] is False


async def test_mid_activity_required_after_giseung(client):
    sh, book_id = await _designed_book(client, email="kid_mid2@test")
    await _finish_giseung(client, sh, book_id)
    ma = (await client.get(f"/books/{book_id}/mid-activity", headers=sh)).json()
    assert ma["required"] is True
    assert len(ma["quiz"]) >= 1 and len(ma["essayBlanks"]) >= 1


async def test_guided_gated_until_mid_activity_done(client):
    sh, book_id = await _designed_book(client, email="kid_mid3@test")
    await _finish_giseung(client, sh, book_id)

    # 중간활동 전: 전·결(guided 4장) 스트림은 conflict 에러.
    events = await _read_sse(client, f"/books/{book_id}/chapters/4/stream", sh)
    err = next((d for e, d in events if e == "error"), None)
    assert err and err["code"] == "conflict"
    assert not any(e == "token" for e, _ in events)

    # 완료 처리 → 게이트 해제.
    done = (await client.post(f"/books/{book_id}/mid-activity/complete", headers=sh)).json()
    assert done["done"] is True
    events2 = await _read_sse(client, f"/books/{book_id}/chapters/4/stream", sh)
    assert any(e == "token" for e, _ in events2)  # 이제 본문 스트리밍


async def test_giseung_complete_triggers_arc_prefetch(client):
    sh, book_id = await _designed_book(client, email="kid_mid4@test")
    await _finish_giseung(client, sh, book_id)
    # 마지막 free 챕터 완료(chapterComplete) 직후 백그라운드 prefetch_arc 로 전·결 선생성.
    store = get_store()
    ch4 = store.get_chapter(book_id, 4)
    assert ch4 is not None and ch4.char_count > 0 and ch4.prefetched is True
