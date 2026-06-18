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


async def test_admin_settings_get_put(client):
    await client.get("/me", headers=ADMIN)
    view = (await client.get("/admin/settings", headers=ADMIN)).json()
    assert "env" in view and "googleApiKey" in view["env"]
    assert view["env"]["googleApiKey"] is False  # 테스트 환경엔 키 없음

    # 허용 키 변경
    r = await client.put("/admin/settings", headers=ADMIN, json={"key": "notify_interval_sec", "value": 120})
    assert r.status_code == 200
    assert r.json()["settings"]["notify_interval_sec"] == 120

    # 시크릿/미허용 키 거부
    bad = await client.put("/admin/settings", headers=ADMIN, json={"key": "google_api_key", "value": "x"})
    assert bad.status_code == 400


async def test_admin_usage_tokens(client):
    from app.store import get_store

    await client.get("/me", headers=ADMIN)
    store = get_store()
    sess = store.create_ai_session("book-t", "writer", "gemini-2.5-flash")
    store.add_token_usage(sess.id, "gemini-2.5-flash", 100, 50, 0.001)
    store.add_token_usage(sess.id, "gemini-2.5-flash", 20, 10, 0.0002)
    r = await client.get("/admin/usage/tokens", headers=ADMIN, params={"groupBy": "model"})
    assert r.status_code == 200
    body = r.json()
    assert body["groupBy"] == "model"
    flash = next(b for b in body["buckets"] if b["key"] == "gemini-2.5-flash")
    assert flash["calls"] == 2
    assert flash["tokensIn"] == 120
    assert body["total"]["tokensOut"] == 60


async def test_notifications_send_list_read(client):
    await client.get("/me", headers=ADMIN)
    r = await client.post("/admin/notifications", headers=ADMIN, json={
        "isBroadcast": True, "title": "점검 안내", "body": "오늘 밤 점검", "level": "info",
    })
    assert r.status_code == 201
    nid = r.json()["id"]
    lst = (await client.get("/admin/notifications", headers=ADMIN)).json()["notifications"]
    assert any(n["id"] == nid for n in lst)
    rr = await client.post(f"/notifications/{nid}/read", headers=ADMIN)
    assert rr.status_code == 200
    unread = (await client.get("/admin/notifications", headers=ADMIN, params={"unread": "true"})).json()["notifications"]
    assert nid not in [n["id"] for n in unread]


async def test_backup_export_import_roundtrip(client):
    from app.store import get_store

    await client.get("/me", headers=ADMIN)
    store = get_store()
    store.create_notification("백업대상", body="b", is_broadcast=True)
    exp = (await client.post("/admin/backup/export", headers=ADMIN, json={"tables": ["notifications"]})).json()
    assert "notifications" in exp["tables"]
    assert len(exp["tables"]["notifications"]) >= 1
    # 미허용 테이블은 무시
    exp2 = (await client.post("/admin/backup/export", headers=ADMIN, json={"tables": ["rate_hits", "notifications"]})).json()
    assert "rate_hits" not in exp2["tables"]

    imp = (await client.post("/admin/backup/import", headers=ADMIN, json={
        "mode": "merge",
        "tables": {"notifications": [{
            "id": "11111111-1111-1111-1111-111111111111", "target_user_id": None,
            "target_role": None, "is_broadcast": True, "title": "복원됨", "body": None,
            "level": "info", "read_at": None, "created_at": "2026-06-18T00:00:00+00:00",
        }]},
    })).json()
    assert imp["imported"]["notifications"] == 1


def test_run_notify_cycle_dedup():
    from app.services.admin import run_notify_cycle
    from app.store.memory import InMemoryStore

    store = InMemoryStore()
    store.add_safety_flag("book1", "u1", "letter", "위험 신호")
    first = run_notify_cycle(store)
    assert first >= 1  # 새 안전신호 → 알림 생성
    second = run_notify_cycle(store)
    assert second == 0  # 새 신호 없음 → dedup


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
