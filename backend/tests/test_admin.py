"""관리자 콘솔(06) — 사용자/메시지/세션 테스트."""
from __future__ import annotations

from tests.conftest import auth

ADMIN = auth("admin@iljjagom.test", "admin")


async def _seed(client):
    th = auth("teacher@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    code = classes[0]["code"]
    sh = auth("kid_admin@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    return th, sh, classes[0]["id"]


async def test_admin_users_list_and_patch(client):
    await _seed(client)
    # admin 진입(프로필 보장)
    await client.get("/me", headers=ADMIN)
    users = (await client.get("/admin/users", headers=ADMIN)).json()["users"]
    emails = {u["email"] for u in users}
    assert "teacher@test" in emails and "kid_admin@test" in emails

    student = next(u for u in users if u["email"] == "kid_admin@test")
    assert student["role"] == "student"
    assert student["classId"]  # 학급 파생

    # 역할 변경
    r = await client.patch(f"/admin/users/{student['id']}", headers=ADMIN, json={"role": "teacher"})
    assert r.status_code == 200
    assert r.json()["role"] == "teacher"


async def test_admin_users_requires_admin(client):
    _, sh, _ = await _seed(client)
    r = await client.get("/admin/users", headers=sh)
    assert r.status_code == 403


async def test_last_admin_cannot_be_demoted(client):
    await client.get("/me", headers=ADMIN)
    users = (await client.get("/admin/users", headers=ADMIN)).json()["users"]
    admin = next(u for u in users if u["email"] == "admin@iljjagom.test")
    r = await client.patch(f"/admin/users/{admin['id']}", headers=ADMIN, json={"role": "student"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


async def test_admin_deactivate_user(client):
    _, sh, _ = await _seed(client)
    await client.get("/me", headers=ADMIN)
    users = (await client.get("/admin/users", headers=ADMIN)).json()["users"]
    student = next(u for u in users if u["email"] == "kid_admin@test")
    r = await client.post(f"/admin/users/{student['id']}/deactivate", headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["status"] == "deactivated"


async def test_admin_messages(client):
    from app.store import get_store

    _, sh, _ = await _seed(client)
    store = get_store()
    store.add_message("book-x", "u1", "user", "tutor", "안녕하세요", session_id="s1")
    msgs = (await client.get("/admin/messages", headers=ADMIN, params={"kind": "tutor"})).json()["messages"]
    assert any(m["content"] == "안녕하세요" for m in msgs)


async def test_admin_sessions_enriched(client):
    th, sh, _ = await _seed(client)
    # 설계 흐름으로 designer 세션 생성
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id = classes[0]["id"]
    await client.post(
        f"/classes/{class_id}/prompts", headers=th,
        json={"topic": "물", "learningObjectives": ["증발"], "assessment": {}},
    )
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)

    sessions = (await client.get("/ai/sessions", headers=ADMIN, params={"role": "designer"})).json()["sessions"]
    assert sessions
    s = sessions[0]
    assert s["role"] == "designer"
    assert s["stepCount"] >= 1
    assert s["userEmail"] == "kid_admin@test"
