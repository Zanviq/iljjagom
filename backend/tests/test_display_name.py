"""표시 이름(Me.name) — 온보딩 채움(이메일 폴백)·/me 노출·관리자 자동 채움·유지."""
from __future__ import annotations

from tests.conftest import auth

ADMIN = "admin@iljjagom.test"


async def test_onboarding_and_me_name_email_fallback(client):
    # dev 토큰은 이름 클레임이 없으므로 이메일 local-part 로 폴백.
    th = auth("teacher_dn@test", "teacher")
    onboard = (await client.post(
        "/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False}
    )).json()
    assert onboard["name"] == "teacher_dn"  # 온보딩 응답에도 name

    me = (await client.get("/me", headers=th)).json()
    assert me["name"] == "teacher_dn"


async def test_student_name_from_email(client):
    th = auth("teacher_dn2@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    code = classes[0]["code"]

    sh = auth("minji@test", "student")
    await client.post(
        "/onboarding", headers=sh,
        json={"role": "student", "classCode": code, "guardianConsent": True},
    )
    me = (await client.get("/me", headers=sh)).json()
    assert me["name"] == "minji"


async def test_admin_name_autofilled(client):
    # 관리자 화이트리스트 자동 프로필도 표시 이름이 채워진다(이메일 local-part).
    ah = auth(ADMIN, "admin")
    me = (await client.get("/me", headers=ah)).json()
    assert me["role"] == "admin"
    assert me["name"] == "admin"


async def test_me_name_null_before_onboarding_then_set(client):
    # 온보딩 전(프로필 없음)에는 name=null(계약: display_name 없으면 null).
    sh = auth("keeper@test", "teacher")
    before = (await client.get("/me", headers=sh)).json()
    assert before["needsOnboarding"] is True
    assert before["name"] is None

    # 온보딩 후 채워지고, 이후 호출에서도 유지.
    await client.post("/onboarding", headers=sh, json={"role": "teacher", "guardianConsent": False})
    me1 = (await client.get("/me", headers=sh)).json()
    assert me1["name"] == "keeper"
    me2 = (await client.get("/me", headers=sh)).json()
    assert me2["name"] == "keeper"
