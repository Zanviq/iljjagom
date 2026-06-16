"""P1 합의 경계(03-기능명세서 §9) 전체 시나리오 + 계약 검증."""
from __future__ import annotations

import json

import pytest

from tests.conftest import auth


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["storage"] == "in-memory"
    assert body["ai"] == "mock"


async def test_me_needs_onboarding(client):
    r = await client.get("/me", headers=auth("kid@test", "student"))
    assert r.status_code == 200
    body = r.json()
    assert body["needsOnboarding"] is True
    assert body["role"] == "student"
    assert body["email"] == "kid@test"


async def test_unauthorized(client):
    r = await client.get("/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


async def test_admin_whitelist(client):
    r = await client.get("/me", headers=auth("admin@iljjagom.test", "student"))
    assert r.json()["role"] == "admin"
    assert r.json()["needsOnboarding"] is False


async def _teacher_makes_prompt(client):
    """교사 온보딩 → 학급 코드 확보 → 발제 1개 생성. (코드, classId, promptId) 반환."""
    th = auth("teacher@test", "teacher")
    r = await client.post(
        "/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False}
    )
    assert r.status_code == 200
    assert r.json()["role"] == "teacher"

    r = await client.get("/classes", headers=th)
    assert r.status_code == 200
    classes = r.json()["classes"]
    assert len(classes) == 1
    class_id = classes[0]["id"]
    code = classes[0]["code"]

    r = await client.post(
        f"/classes/{class_id}/prompts",
        headers=th,
        json={
            "topic": "물의 순환",
            "learningObjectives": ["증발·응결·강수 이해", "관련 어휘 5개"],
            "assessment": {"type": "quiz", "detail": "5문항"},
            "language": "ko",
        },
    )
    assert r.status_code == 201
    prompt = r.json()
    assert prompt["classId"] == class_id
    assert prompt["topic"] == "물의 순환"
    return code, class_id, prompt["id"]


async def test_full_p1_vertical_slice(client):
    # 1. 교사: 발제 생성
    code, class_id, prompt_id = await _teacher_makes_prompt(client)

    # 2. 학생: 온보딩(학급 코드) → 책 생성
    sh = auth("kid@test", "student")
    r = await client.post(
        "/onboarding",
        headers=sh,
        json={"role": "student", "classCode": code, "guardianConsent": True, "grade": 4},
    )
    assert r.status_code == 200
    assert r.json()["needsOnboarding"] is False

    # 학생은 학급 발제를 볼 수 있다
    r = await client.get(f"/classes/{class_id}/prompts", headers=sh)
    assert r.status_code == 200
    assert len(r.json()["prompts"]) == 1

    r = await client.post("/books", headers=sh, json={"promptId": prompt_id})
    assert r.status_code == 201
    book = r.json()
    assert book["status"] == "planning"
    assert book["classId"] == class_id
    book_id = book["id"]

    # 3. 기획 대화 몇 번
    for msg in ["주인공은 용감한 토끼야", "숲속에 살아", "호기심이 많아"]:
        r = await client.post(
            f"/books/{book_id}/plan/messages", headers=sh, json={"message": msg}
        )
        assert r.status_code == 200
        reply = r.json()
        assert "reply" in reply
        assert "characterDraft" in reply
    assert reply["readyToWrite"] is True
    assert "용감함" in reply["characterDraft"]["traits"]

    # 4. 설계 → Bible 생성
    r = await client.post(f"/books/{book_id}/design", headers=sh)
    assert r.status_code == 202
    design = r.json()
    assert design["status"] == "done"
    assert design["totalChaptersPlanned"] == 6

    # 책 상태 writing 으로 전이 + 챕터 골격
    r = await client.get(f"/books/{book_id}", headers=sh)
    detail = r.json()
    assert detail["status"] == "writing"
    assert detail["totalChaptersPlanned"] == 6
    assert len(detail["chapters"]) == 6
    assert detail["chapters"][0]["mode"] == "free"
    assert detail["chapters"][-1]["mode"] == "guided"

    # 5. 1챕터 SSE 스트림
    events = await _read_sse(client, f"/books/{book_id}/chapters/1/stream", sh)
    types = [e[0] for e in events]
    assert types[0] == "meta"
    assert "token" in types
    assert types[-1] == "done"
    meta = events[0][1]
    assert meta["chapterIdx"] == 1
    done = events[-1][1]
    assert done["chapterIdx"] == 1
    assert done["nextChapterAvailable"] is True
    assert done["charCount"] > 0

    # 본문이 토큰을 이어 붙인 것과 일치하는지 (글자 단위 흐름 확인)
    body = "".join(e[1]["text"] for e in events if e[0] == "token")
    assert len(body) == done["charCount"]

    # 단어 도움 최소판
    r = await client.get(
        f"/books/{book_id}/words", headers=sh, params={"term": "수증기"}
    )
    assert r.status_code == 200
    assert r.json()["term"] == "수증기"


async def test_guided_chapter_has_illustration_first(client):
    code, class_id, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid2@test", "student")
    await client.post(
        "/onboarding",
        headers=sh,
        json={"role": "student", "classCode": code, "guardianConsent": True},
    )
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)

    # 유도(guided) 챕터(4장)는 illustration/prompt 가 token 보다 먼저.
    events = await _read_sse(client, f"/books/{book_id}/chapters/4/stream", sh)
    types = [e[0] for e in events]
    assert types[0] == "meta"
    assert "illustration" in types
    assert "prompt" in types
    assert types.index("illustration") < types.index("token")
    assert types.index("prompt") < types.index("token")


async def test_role_guard_student_cannot_make_prompt(client):
    sh = auth("kid@test", "student")
    r = await client.post(
        "/classes/some-id/prompts",
        headers=sh,
        json={"topic": "x", "learningObjectives": ["y"]},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


async def test_safety_blocks_bad_input(client):
    code, class_id, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid3@test", "student")
    await client.post(
        "/onboarding", headers=sh, json={"role": "student", "classCode": code}
    )
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    r = await client.post(
        f"/books/{book_id}/plan/messages", headers=sh, json={"message": "다 죽여버릴거야"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


async def test_onboarding_invalid_code(client):
    sh = auth("kid4@test", "student")
    r = await client.post(
        "/onboarding", headers=sh, json={"role": "student", "classCode": "ZZZZZZ"}
    )
    assert r.status_code == 400


async def _read_sse(client, url: str, headers: dict) -> list[tuple[str, dict]]:
    """SSE 응답을 (event, data) 목록으로 파싱."""
    events: list[tuple[str, dict]] = []
    async with client.stream("GET", url, headers=headers) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        event_name = None
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
                events.append((event_name, data))
            elif line.startswith(":"):
                continue  # 하트비트
    return events
