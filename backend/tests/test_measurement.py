"""측정(04) 테스트 — events 배치 수집 + learning-results 저장/조회(learning_artifacts)."""
from __future__ import annotations

from tests.conftest import auth


async def _student_book(client, email="kid_m@test"):
    th = auth("teacher@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(
        f"/classes/{class_id}/prompts", headers=th,
        json={"topic": "물", "learningObjectives": ["증발"], "assessment": {}},
    )
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth(email, "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    return class_id, code, prompt_id, sh, th, book_id


async def test_events_batch_accepts_and_drops_unauthorized(client):
    class_id, code, prompt_id, sh, th, book_id = await _student_book(client)
    r = await client.post(
        "/events", headers=sh,
        json={"events": [
            {"bookId": book_id, "type": "chapter_open", "payload": {"chapterIdx": 1}},
            {"bookId": None, "type": "learning_open", "payload": {}},
            {"bookId": "00000000-0000-0000-0000-000000000000", "type": "chapter_done", "payload": {}},
        ]},
    )
    assert r.status_code == 202
    # 권한 없는(존재X) book 이벤트는 누락 → 2개만 accepted
    assert r.json()["accepted"] == 2


async def test_learning_result_quiz_save_and_list(client):
    _, _, _, sh, _, book_id = await _student_book(client)
    r = await client.post(
        f"/books/{book_id}/learning-results", headers=sh,
        json={"type": "quiz", "data": {"answers": [{"index": 0, "picked": 0, "correct": True, "objective": "증발"}], "score": 1, "total": 1}},
    )
    assert r.status_code == 201
    assert r.json()["type"] == "quiz"
    lst = (await client.get(f"/books/{book_id}/learning-results", headers=sh)).json()["results"]
    assert any(x["type"] == "quiz" and x["data"]["score"] == 1 for x in lst)


async def test_learning_result_essay_safety_block(client):
    _, _, _, sh, _, book_id = await _student_book(client)
    r = await client.post(
        f"/books/{book_id}/learning-results", headers=sh,
        json={"type": "essay", "data": {"blanks": [{"prompt": "느낌은?", "text": "죽여 버리고 싶었다"}]}},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


async def test_letter_also_saved_as_learning_result(client):
    _, _, _, sh, _, book_id = await _student_book(client)
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    await client.post(f"/books/{book_id}/letters", headers=sh, json={"to": "주인공", "body": "고마워"})
    results = (await client.get(f"/books/{book_id}/learning-results", headers=sh)).json()["results"]
    assert any(x["type"] == "letter" and x["data"]["status"] == "answered" for x in results)


async def test_learning_result_forbidden_other_student(client):
    _, code, prompt_id, sh, th, book_id = await _student_book(client)
    other = auth("intruder_m@test", "student")
    await client.post("/onboarding", headers=other, json={"role": "student", "classCode": code, "guardianConsent": True})
    r = await client.post(
        f"/books/{book_id}/learning-results", headers=other,
        json={"type": "quiz", "data": {"score": 0, "total": 1}},
    )
    assert r.status_code == 403
