"""기획 인터뷰 종료(학생/03) — readyToWrite 후 질문 멈춤·공감만, interviewClosed 신호."""
from __future__ import annotations

from app.ai.chat import _strip_trailing_question
from tests.conftest import auth


def test_strip_trailing_question():
    assert _strip_trailing_question("와, 멋져요! 그럼 산은 어떤가요?") == "와, 멋져요!"
    assert _strip_trailing_question("정말 좋아요.") == "정말 좋아요."
    # 전부 질문이면 기본 칭찬으로 폴백.
    assert "?" not in _strip_trailing_question("어떤가요?")


async def _student(client, email="kid_iv@test"):
    th = auth("teacher_iv@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth(email, "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    return sh, book_id


async def test_interview_stops_questioning_after_ready(client):
    sh, book_id = await _student(client)
    r1 = (await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})).json()
    assert r1["readyToWrite"] is False
    assert r1["interviewClosed"] is False
    assert "?" in r1["reply"]  # 아직 질문 진행

    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "숲에 살아요"})
    r3 = (await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "친구는 다람쥐"})).json()
    assert r3["readyToWrite"] is True
    assert r3["interviewClosed"] is True
    assert "?" not in r3["reply"]  # 준비 완료 → 새 질문 없음(공감만)
