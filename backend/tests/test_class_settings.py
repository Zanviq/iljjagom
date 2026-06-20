"""학급 설정·발제 확장·안전강도 해석 체인·대시보드 기록(선생님/02)."""
from __future__ import annotations

from app.services.policy import resolve_safety_level
from app.store import get_store
from tests.conftest import auth


async def _teacher_class(client, email="teacher_cs@test"):
    th = auth(email, "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    cls = (await client.get("/classes", headers=th)).json()["classes"][0]
    return th, cls["id"], cls["code"]


async def test_class_settings_get_put(client):
    th, class_id, _ = await _teacher_class(client)
    got = (await client.get(f"/classes/{class_id}/settings", headers=th)).json()
    assert got["defaults"]["safetyLevel"] == "standard"

    put = await client.put(f"/classes/{class_id}/settings", headers=th,
                           json={"value": {"safetyLevel": "relaxed", "featureToggles": {"board": True}}})
    assert put.status_code == 200
    assert put.json()["value"]["safetyLevel"] == "relaxed"

    # 미허용 키는 무시(시크릿/모델 무단설정 차단).
    put2 = await client.put(f"/classes/{class_id}/settings", headers=th,
                            json={"value": {"models": {"writer": "evil"}}})
    assert "models" not in put2.json()["value"]

    # 잘못된 안전강도 → 400.
    bad = await client.put(f"/classes/{class_id}/settings", headers=th,
                           json={"value": {"safetyLevel": "loose"}})
    assert bad.status_code == 400


async def test_settings_feature_toggles_default_and_sync(client):
    th, class_id, _ = await _teacher_class(client, email="teacher_cs_ft@test")
    got = (await client.get(f"/classes/{class_id}/settings", headers=th)).json()
    # featureToggles 기본값에 boardAutoPublish 노출(프론트가 토글 렌더 가능, 이슈3).
    assert "boardAutoPublish" in got["defaults"]["featureToggles"]
    # featureToggles.boardAutoPublish 저장 → classrooms 컬럼 동기.
    put = await client.put(f"/classes/{class_id}/settings", headers=th,
                           json={"value": {"featureToggles": {"boardAutoPublish": True}}})
    assert put.status_code == 200
    assert put.json()["value"]["featureToggles"]["boardAutoPublish"] is True
    assert get_store().get_classroom(class_id).board_auto_publish is True


async def test_safety_resolution_chain(client):
    th, class_id, code = await _teacher_class(client, email="teacher_cs2@test")
    # 발제 안전강도 오버라이드.
    await client.post(f"/classes/{class_id}/prompts", headers=th, json={
        "topic": "물", "learningObjectives": ["증발"], "assessment": {}, "safetyLevel": "strict",
    })
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth("kid_cs@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]

    store = get_store()
    # 발제 > 학급 > 전역: 발제가 strict 이므로 strict.
    assert resolve_safety_level(store, book_id) == "strict"
    # 학급 설정만 있을 때(발제 미지정 책)는 학급값.
    store.upsert_class_settings(class_id, {"safetyLevel": "relaxed"}, th["Authorization"])
    store.update_prompt(prompt_id, safety_level=None)
    assert resolve_safety_level(store, book_id) == "relaxed"


async def test_prompt_update_and_close_blocks_new_books(client):
    th, class_id, code = await _teacher_class(client, email="teacher_cs3@test")
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]

    # 발제 수정(권장 학년·장수).
    patched = await client.patch(f"/classes/{class_id}/prompts/{prompt_id}", headers=th,
                                 json={"gradeBand": 4, "chaptersPlanned": 5})
    assert patched.json()["gradeBand"] == 4 and patched.json()["chaptersPlanned"] == 5

    # 마감 → 학생 새 책 생성 차단.
    closed = await client.post(f"/classes/{class_id}/prompts/{prompt_id}/close", headers=th)
    assert closed.json()["status"] == "closed"
    sh = auth("kid_cs3@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    r = await client.post("/books", headers=sh, json={"promptId": prompt_id})
    assert r.status_code == 409


async def test_dashboard_history(client):
    th, class_id, code = await _teacher_class(client, email="teacher_cs4@test")
    hist = (await client.get(f"/classes/{class_id}/dashboard/history?groupBy=day", headers=th)).json()
    assert "buckets" in hist and "totals" in hist
