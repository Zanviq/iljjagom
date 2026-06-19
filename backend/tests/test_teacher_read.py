"""교사 학생 데이터 열람(선생님/03) + 발제별 집계(선생님/05)."""
from __future__ import annotations

from tests.conftest import auth


async def _setup(client):
    th = auth("teacher_tr@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    cls = (await client.get("/classes", headers=th)).json()["classes"][0]
    class_id, code = cls["id"], cls["code"]
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth("kid_tr@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    async with client.stream("GET", f"/books/{book_id}/chapters/1/stream", headers=sh) as resp:
        async for _ in resp.aiter_lines():
            pass
    return th, sh, class_id, prompt_id, book_id


async def test_teacher_reads_student_work(client):
    th, sh, class_id, prompt_id, book_id = await _setup(client)

    # 챕터 본문 열람(스트림 미트리거).
    content = (await client.get(f"/books/{book_id}/chapters", headers=th)).json()
    assert content["chapters"][0]["body"]

    single = (await client.get(f"/books/{book_id}/chapters/1/content", headers=th)).json()
    assert single["idx"] == 1 and single["charCount"] > 0

    # 기획 대화·설계 열람.
    plan = (await client.get(f"/books/{book_id}/plan-messages", headers=th)).json()
    assert any(m["role"] == "student" and "토끼" in m["content"] for m in plan["messages"])
    bible = (await client.get(f"/books/{book_id}/bible", headers=th)).json()
    assert bible["bible"].get("characters")

    # 학생 책 목록(담당 학급).
    sid = (await client.get("/me", headers=sh)).json()["id"]
    sbooks = (await client.get(f"/classes/{class_id}/students/{sid}/books", headers=th)).json()
    assert any(b["id"] == book_id for b in sbooks["books"])


async def test_other_teacher_blocked(client):
    th, sh, class_id, prompt_id, book_id = await _setup(client)
    other = auth("teacher_tr2@test", "teacher")
    await client.post("/onboarding", headers=other, json={"role": "teacher", "guardianConsent": False})
    # 타 학급 교사는 본문 열람 불가(can_access_book 차단).
    assert (await client.get(f"/books/{book_id}/chapters", headers=other)).status_code == 403


async def test_prompt_submissions(client):
    th, sh, class_id, prompt_id, book_id = await _setup(client)
    sub = (await client.get(f"/classes/{class_id}/prompts/{prompt_id}/submissions", headers=th)).json()
    assert sub["counts"]["enrolled"] >= 1 and sub["counts"]["started"] == 1
    row = next(s for s in sub["submissions"] if s["bookId"] == book_id)
    assert row["chaptersDone"] == 1 and row["charTotal"] > 0
    assert sub["prompt"]["id"] == prompt_id
