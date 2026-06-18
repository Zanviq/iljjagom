"""학습 교재 캐싱(학생/13) — 1회 생성·영속화, 시그니처 변동 시 재생성, 결과조회 분리."""
from __future__ import annotations

from app.store import get_store
from tests.conftest import auth


async def _book_with_chapter(client, email="kid_lc@test"):
    th = auth("teacher_lc@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(
        f"/classes/{class_id}/prompts", headers=th,
        json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}},
    )
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth(email, "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    await _drain(client, f"/books/{book_id}/chapters/1/stream", sh)  # ch1 집필
    return sh, book_id


async def _drain(client, url, headers):
    async with client.stream("GET", url, headers=headers) as resp:
        async for _ in resp.aiter_lines():
            pass


async def test_learning_cached_and_served(client):
    sh, book_id = await _book_with_chapter(client)
    store = get_store()

    first = (await client.get(f"/books/{book_id}/learning", headers=sh)).json()
    assert first["quiz"]  # 생성됨
    sets = store.list_learning_artifacts(book_id=book_id, type="learning_set")
    assert len(sets) == 1  # 캐시 1행 저장

    # 캐시 행을 표식으로 변조 → 두 번째 호출이 재생성이 아니라 캐시를 반환하는지 검증.
    sets[0].data["vocab"] = [{"term": "CACHED", "reading": "x", "meaning": "표식"}]
    second = (await client.get(f"/books/{book_id}/learning", headers=sh)).json()
    assert any(v["term"] == "CACHED" for v in second["vocab"])  # 캐시 적중(재생성 아님)
    # 캐시 행이 중복 생성되지 않는다.
    assert len(store.list_learning_artifacts(book_id=book_id, type="learning_set")) == 1


async def test_learning_regenerated_on_signature_change(client):
    sh, book_id = await _book_with_chapter(client, email="kid_lc2@test")
    store = get_store()
    (await client.get(f"/books/{book_id}/learning", headers=sh)).json()
    sets = store.list_learning_artifacts(book_id=book_id, type="learning_set")
    sets[0].data["vocab"] = [{"term": "CACHED", "reading": "x", "meaning": "표식"}]

    # 다음 장 집필 → 시그니처 변동 → 재생성(표식 사라짐).
    await _drain(client, f"/books/{book_id}/chapters/2/stream", sh)
    after = (await client.get(f"/books/{book_id}/learning", headers=sh)).json()
    assert not any(v["term"] == "CACHED" for v in after["vocab"])
    assert len(store.list_learning_artifacts(book_id=book_id, type="learning_set")) == 2


async def test_learning_results_excludes_cache(client):
    sh, book_id = await _book_with_chapter(client, email="kid_lc3@test")
    await client.get(f"/books/{book_id}/learning", headers=sh)  # learning_set 캐시 생성
    # 학생 자기보고 결과 1건 저장.
    await client.post(
        f"/books/{book_id}/learning-results", headers=sh,
        json={"type": "quiz", "data": {"score": 1, "total": 1}},
    )
    results = (await client.get(f"/books/{book_id}/learning-results", headers=sh)).json()["results"]
    assert all(r["type"] != "learning_set" for r in results)  # 캐시는 결과에서 제외
    assert any(r["type"] == "quiz" for r in results)


async def test_empty_book_not_cached(client):
    # 집필 0장이면 캐시를 만들지 않는다(이후 집필 시 정상 생성).
    th = auth("teacher_lc4@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth("kid_lc4@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]

    await client.get(f"/books/{book_id}/learning", headers=sh)  # 집필 전
    assert get_store().list_learning_artifacts(book_id=book_id, type="learning_set") == []
