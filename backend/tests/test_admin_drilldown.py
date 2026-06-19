"""관리자 드릴다운(관리자/01) + 설정 스키마(관리자/02)."""
from __future__ import annotations

from tests.conftest import auth

ADMIN = "admin@iljjagom.test"


async def _setup(client):
    th = auth("teacher_ad@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    cls = (await client.get("/classes", headers=th)).json()["classes"][0]
    class_id, code = cls["id"], cls["code"]
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth("kid_ad@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    sid = (await client.get("/me", headers=sh)).json()["id"]
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    # 총괄 AI 대화(overseer 세션 + 메시지).
    await client.post("/ai/overseer/messages", headers=sh, json={"message": "지금까지 한 거 알려줘"})
    return sh, sid, class_id, prompt_id, book_id


async def test_user_overview(client):
    sh, sid, class_id, prompt_id, book_id = await _setup(client)
    ah = auth(ADMIN, "admin")
    ov = (await client.get(f"/admin/users/{sid}/overview", headers=ah)).json()
    assert ov["user"]["id"] == sid
    assert any(b["id"] == book_id for b in ov["books"])
    assert ov["books"][0]["sessionCount"] >= 1  # 설계 세션
    assert isinstance(ov["recentMessages"], list)


async def test_book_timeline(client):
    sh, sid, class_id, prompt_id, book_id = await _setup(client)
    ah = auth(ADMIN, "admin")
    tl = (await client.get(f"/admin/books/{book_id}/timeline", headers=ah)).json()
    assert tl["book"]["id"] == book_id
    assert tl["prompt"]["id"] == prompt_id
    assert len(tl["chapters"]) >= 1
    assert any(m["role"] == "student" for m in tl["planMessages"])
    assert any(s["stage"] == "설계(Bible)" for s in tl["sessions"])


async def test_session_detail_transcript_and_context(client):
    sh, sid, class_id, prompt_id, book_id = await _setup(client)
    ah = auth(ADMIN, "admin")
    sessions = (await client.get("/ai/sessions?role=overseer", headers=ah)).json()["sessions"]
    ov = next(s for s in sessions if s["userId"] == sid)
    assert ov["stage"] == "총괄(곰 작가)"
    detail = (await client.get(f"/ai/sessions/{ov['id']}", headers=ah)).json()
    assert detail["context"]["stage"] == "총괄(곰 작가)"
    assert any(m["role"] == "user" for m in detail["transcript"])  # 대화 전문


async def test_messages_group_by_user(client):
    sh, sid, *_ = await _setup(client)
    ah = auth(ADMIN, "admin")
    grouped = (await client.get("/admin/messages?groupBy=user", headers=ah)).json()
    row = next(u for u in grouped["users"] if u["userId"] == sid)
    assert row["messageCount"] >= 1


async def test_settings_schema_and_enum_validation(client):
    ah = auth(ADMIN, "admin")
    schema = (await client.get("/admin/settings/schema", headers=ah)).json()
    # 스키마는 raw 키(snake_case) 그대로 노출 — 콘솔이 키별 컨트롤 렌더.
    assert schema["schema"]["safety_level"]["options"] == ["relaxed", "standard", "strict"]
    # 잘못된 enum → 400.
    bad = await client.put("/admin/settings", headers=ah, json={"key": "safety_level", "value": "loose"})
    assert bad.status_code == 400
    ok = await client.put("/admin/settings", headers=ah, json={"key": "safety_level", "value": "standard"})
    assert ok.status_code == 200
