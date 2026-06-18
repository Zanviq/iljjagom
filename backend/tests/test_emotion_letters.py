"""감정 곡선 학생 입력(학생/11) + 편지 인물 선택지(학생/12)."""
from __future__ import annotations

from tests.conftest import auth


async def _written_book(client, email="kid_em@test"):
    th = auth("teacher_em@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth(email, "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    async with client.stream("GET", f"/books/{book_id}/chapters/1/stream", headers=sh) as resp:
        async for _ in resp.aiter_lines():
            pass
    return sh, book_id


async def test_learning_has_letter_characters(client):
    sh, book_id = await _written_book(client)
    learning = (await client.get(f"/books/{book_id}/learning", headers=sh)).json()
    chars = learning["letterCharacters"]
    assert chars and all({"id", "name", "traits"} <= set(c) for c in chars)
    assert any(c["name"] == "주인공" for c in chars)  # mock Bible 인물


async def test_emotion_is_input_frame(client):
    sh, book_id = await _written_book(client, email="kid_em2@test")
    emo = (await client.get(f"/books/{book_id}/learning", headers=sh)).json()["emotion"]
    assert "슬픔" in emo["labels"]
    assert emo["points"][0]["label"] is None and emo["points"][0]["value"] is None


async def test_emotion_save_and_validation(client):
    sh, book_id = await _written_book(client, email="kid_em3@test")
    # 유효 저장.
    ok = await client.post(f"/books/{book_id}/learning-results", headers=sh, json={
        "type": "emotion", "data": {"points": [{"chapterIdx": 1, "label": "설렘", "value": 0.6}]},
    })
    assert ok.status_code == 201
    results = (await client.get(f"/books/{book_id}/learning-results", headers=sh)).json()["results"]
    assert any(r["type"] == "emotion" for r in results)

    # 라벨 화이트리스트 위반 → 400.
    bad_label = await client.post(f"/books/{book_id}/learning-results", headers=sh, json={
        "type": "emotion", "data": {"points": [{"chapterIdx": 1, "label": "아무거나", "value": 0.5}]},
    })
    assert bad_label.status_code == 400
    # value 범위 위반 → 400.
    bad_val = await client.post(f"/books/{book_id}/learning-results", headers=sh, json={
        "type": "emotion", "data": {"points": [{"chapterIdx": 1, "label": "설렘", "value": 5}]},
    })
    assert bad_val.status_code == 400
    # 없는 장 → 400.
    bad_ch = await client.post(f"/books/{book_id}/learning-results", headers=sh, json={
        "type": "emotion", "data": {"points": [{"chapterIdx": 99, "label": "설렘", "value": 0.5}]},
    })
    assert bad_ch.status_code == 400
