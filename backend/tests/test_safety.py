"""안전·교사검토 루프 테스트 — 보류 편지 영속화 → 교사 승인/반려 → 플래그 종결."""
from __future__ import annotations

from app.ai import safety as safety_gate
from tests.conftest import auth


def test_input_categorization():
    r = safety_gate.check_input("죽여 버릴거야")
    assert r.ok is False
    assert r.category == "violence"
    r2 = safety_gate.check_input("씨   발")  # 공백 정규화 우회 차단
    assert r2.ok is False
    assert r2.category == "profanity"
    ok = safety_gate.check_input("오늘은 즐거운 하루였어")
    assert ok.ok is True
    assert ok.category is None


def test_input_risk_signal_not_blocked():
    r = safety_gate.check_input("혼자라서 너무 외로워")
    assert r.ok is True  # 차단 아님(보류 대상)
    assert r.risk is True


def test_filter_output_flags_heavy_scene():
    out = safety_gate.filter_output("주인공이 죽었어요.", safety_level="strict")
    assert out.ok is True  # 학생 흐름 막지 않음
    assert out.flags
    assert out.softened is True
    clean = safety_gate.filter_output("주인공이 신나게 뛰어놀았어요.")
    assert not clean.flags


async def _setup(client):
    """교사 발제 → 학생 책+설계. (classId, code, promptId, 학생헤더, 교사헤더, bookId) 반환."""
    th = auth("teacher@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(
        f"/classes/{class_id}/prompts", headers=th,
        json={"topic": "우정", "learningObjectives": ["배려"], "assessment": {}},
    )
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth("kid_sf@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    return class_id, code, prompt_id, sh, th, book_id


async def test_consent_required_blocks_book_creation(client):
    # 보호자 미동의 학생은 책 생성이 consent_required(403)로 차단된다.
    th = auth("teacher@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(
        f"/classes/{class_id}/prompts", headers=th,
        json={"topic": "우정", "learningObjectives": ["배려"], "assessment": {}},
    )
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]

    sh = auth("kid_noconsent@test", "student")
    # 동의 없이 온보딩
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code})
    r = await client.post("/books", headers=sh, json={"promptId": prompt_id})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "consent_required"


async def test_answered_letter_persisted(client):
    _, _, _, sh, _, book_id = await _setup(client)
    r = await client.post(
        f"/books/{book_id}/letters", headers=sh, json={"to": "주인공", "body": "안녕 주인공아 고마워"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "answered"
    assert body["reply"]
    assert body["letterId"]
    # 학생이 자기 편지 목록에서 확인
    lst = (await client.get(f"/books/{book_id}/letters", headers=sh)).json()["letters"]
    assert any(m["id"] == body["letterId"] and m["status"] == "answered" for m in lst)


async def test_held_letter_review_approve_flow(client):
    class_id, _, _, sh, th, book_id = await _setup(client)
    # 정서 위험 신호 → 보류
    r = await client.post(
        f"/books/{book_id}/letters", headers=sh, json={"to": "주인공", "body": "혼자라서 너무 외로워"}
    )
    assert r.json()["status"] == "held"
    letter_id = r.json()["letterId"]
    assert letter_id

    # 교사: 보류 편지 목록
    held = (await client.get(f"/classes/{class_id}/letters", headers=th, params={"status": "held"})).json()["letters"]
    assert any(m["id"] == letter_id for m in held)
    # 교사: 안전 신호 목록(open) + 연결 편지
    flags = (await client.get(f"/classes/{class_id}/safety-flags", headers=th, params={"status": "open"})).json()["flags"]
    flag = next(f for f in flags if f["letterId"] == letter_id)
    assert flag["severity"] == "high"
    detail = (await client.get(f"/safety-flags/{flag['id']}", headers=th)).json()
    assert detail["letter"]["body"] == "혼자라서 너무 외로워"

    # 교사 승인(직접 답장)
    appr = await client.post(
        f"/letters/{letter_id}/approve", headers=th, json={"reply": "괜찮아, 네 곁에 있어."}
    )
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"
    assert appr.json()["reply"] == "괜찮아, 네 곁에 있어."

    # 연결 플래그 자동 resolved
    flags_after = (await client.get(f"/classes/{class_id}/safety-flags", headers=th, params={"status": "open"})).json()["flags"]
    assert not any(f["id"] == flag["id"] for f in flags_after)
    # 학생이 승인된 답장 확인
    lst = (await client.get(f"/books/{book_id}/letters", headers=sh)).json()["letters"]
    assert any(m["id"] == letter_id and m["status"] == "approved" and m["reply"] for m in lst)


async def test_held_letter_reject_flow(client):
    class_id, _, _, sh, th, book_id = await _setup(client)
    r = await client.post(
        f"/books/{book_id}/letters", headers=sh, json={"to": "주인공", "body": "아무도 없는 것 같아"}
    )
    letter_id = r.json()["letterId"]
    rej = await client.post(f"/letters/{letter_id}/reject", headers=th, json={"note": "대면 상담 필요"})
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"


async def test_approve_with_ai_reply(client):
    class_id, _, _, sh, th, book_id = await _setup(client)
    r = await client.post(
        f"/books/{book_id}/letters", headers=sh, json={"to": "주인공", "body": "혼자라서 슬퍼"}
    )
    letter_id = r.json()["letterId"]
    appr = await client.post(f"/letters/{letter_id}/approve", headers=th, json={"useAiReply": True})
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"
    assert appr.json()["reply"]  # AI 페르소나 답장 생성됨
    assert appr.json()["replySource"] == "ai"


async def test_review_forbidden_for_other_student(client):
    class_id, code, prompt_id, sh, th, book_id = await _setup(client)
    r = await client.post(
        f"/books/{book_id}/letters", headers=sh, json={"to": "주인공", "body": "혼자라서 외로워"}
    )
    letter_id = r.json()["letterId"]
    intruder = auth("intruder@test", "student")
    # 학생은 검토 엔드포인트(teacher/admin 전용) 접근 불가 → 403
    rr = await client.post(f"/letters/{letter_id}/reject", headers=intruder, json={"note": "x"})
    assert rr.status_code == 403
    fr = await client.get(f"/classes/{class_id}/safety-flags", headers=intruder)
    assert fr.status_code == 403


async def test_other_teacher_cannot_review(client):
    class_id, _, _, sh, th, book_id = await _setup(client)
    r = await client.post(
        f"/books/{book_id}/letters", headers=sh, json={"to": "주인공", "body": "혼자라서 외로워"}
    )
    letter_id = r.json()["letterId"]
    # 다른 교사(다른 학급) → 담당 아님 403
    other_t = auth("other_teacher@test", "teacher")
    await client.post("/onboarding", headers=other_t, json={"role": "teacher", "guardianConsent": False})
    rr = await client.post(f"/letters/{letter_id}/reject", headers=other_t, json={"note": "x"})
    assert rr.status_code == 403
