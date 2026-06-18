"""AI 세션/트레이스 API 테스트 — 관리자 조회 + ask_user answer 재개."""
from __future__ import annotations

from tests.conftest import auth


async def _student_book(client):
    """교사 발제 → 학생 온보딩 → 책 생성 → 설계(designer 세션 발생). (book_id, 학생헤더) 반환."""
    th = auth("teacher@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(
        f"/classes/{class_id}/prompts", headers=th,
        json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}},
    )
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth("kid_sess@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    return book_id, sh


async def test_admin_lists_and_reads_sessions(client):
    book_id, _ = await _student_book(client)
    ah = auth("admin@iljjagom.test", "admin")

    r = await client.get("/ai/sessions", headers=ah, params={"bookId": book_id})
    assert r.status_code == 200
    sessions = r.json()["sessions"]
    assert any(s["role"] == "designer" for s in sessions)

    sid = sessions[0]["id"]
    r2 = await client.get(f"/ai/sessions/{sid}", headers=ah)
    assert r2.status_code == 200
    detail = r2.json()
    assert "steps" in detail
    assert len(detail["steps"]) >= 1
    assert "skill" in detail["steps"][0]


async def test_sessions_requires_admin(client):
    _, sh = await _student_book(client)
    r = await client.get("/ai/sessions", headers=sh)
    assert r.status_code == 403


async def test_answer_resumes_awaiting_session(client):
    from app.store import get_store

    book_id, sh = await _student_book(client)
    store = get_store()
    sess = store.create_ai_session(book_id, "chat", "m")
    store.update_ai_session(sess.id, status="awaiting_user")

    r = await client.post(
        f"/ai/sessions/{sess.id}/answer", headers=sh, json={"choice": "별이"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    # 응답이 messages + 스텝으로 기록됨
    msgs = store.list_messages(book_id, kind="tutor")
    assert any(m.content == "별이" for m in msgs)
    steps = store.list_ai_steps(sess.id)
    assert steps[-1].skill == "user_answer"


async def test_answer_conflict_when_not_awaiting(client):
    from app.store import get_store

    book_id, sh = await _student_book(client)
    store = get_store()
    sess = store.create_ai_session(book_id, "chat", "m")  # running, not awaiting
    r = await client.post(f"/ai/sessions/{sess.id}/answer", headers=sh, json={"text": "안녕"})
    assert r.status_code == 409


async def test_answer_forbidden_for_other_student(client):
    from app.store import get_store

    book_id, _ = await _student_book(client)
    store = get_store()
    sess = store.create_ai_session(book_id, "chat", "m")
    store.update_ai_session(sess.id, status="awaiting_user")
    other = auth("intruder@test", "student")
    r = await client.post(f"/ai/sessions/{sess.id}/answer", headers=other, json={"text": "x"})
    assert r.status_code == 403
