"""다중 학급(선생님/01) — 생성·이름변경·코드 재발급·소유 경계."""
from __future__ import annotations

from tests.conftest import auth


async def _teacher(client, email="teacher_mc@test"):
    th = auth(email, "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    return th


async def test_create_and_list_multiple_classes(client):
    th = await _teacher(client)
    before = (await client.get("/classes", headers=th)).json()["classes"]
    assert len(before) == 1  # 온보딩 기본 학급

    created = await client.post("/classes", headers=th, json={"name": "2반"})
    assert created.status_code == 201
    assert created.json()["name"] == "2반" and created.json()["code"]

    after = (await client.get("/classes", headers=th)).json()["classes"]
    assert len(after) == 2


async def test_rename_class(client):
    th = await _teacher(client, email="teacher_mc2@test")
    class_id = (await client.get("/classes", headers=th)).json()["classes"][0]["id"]
    r = await client.patch(f"/classes/{class_id}", headers=th, json={"name": "햇살반"})
    assert r.status_code == 200 and r.json()["name"] == "햇살반"


async def test_rotate_code_blocks_old_keeps_enrollment(client):
    th = await _teacher(client, email="teacher_mc3@test")
    cls = (await client.get("/classes", headers=th)).json()["classes"][0]
    class_id, old_code = cls["id"], cls["code"]

    # 학생 가입(기존 코드).
    sh = auth("kid_mc@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": old_code, "guardianConsent": True})

    rot = (await client.post(f"/classes/{class_id}/rotate-code", headers=th)).json()
    assert rot["code"] != old_code

    # 기존 코드로는 신규 가입 불가.
    sh2 = auth("kid_mc2@test", "student")
    await client.post("/onboarding", headers=sh2, json={"role": "student", "classCode": old_code, "guardianConsent": True})
    me2 = (await client.get("/me", headers=sh2)).json()
    assert me2["classId"] is None  # 가입 안 됨

    # 이미 가입한 학생은 영향 없음.
    me = (await client.get("/me", headers=sh)).json()
    assert me["classId"] == class_id


async def test_other_teacher_cannot_modify(client):
    th = await _teacher(client, email="teacher_mc4@test")
    class_id = (await client.get("/classes", headers=th)).json()["classes"][0]["id"]
    other = await _teacher(client, email="teacher_mc5@test")
    r = await client.patch(f"/classes/{class_id}", headers=other, json={"name": "탈취"})
    assert r.status_code == 403
