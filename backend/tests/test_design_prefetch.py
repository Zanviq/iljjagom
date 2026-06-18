"""설계 백그라운드 선생성(학생/04) — readyToWrite 트리거·즉시 진입·stale 재생성."""
from __future__ import annotations

from app.store import get_store
from tests.conftest import auth


async def _planned_book(client, msgs: int, email="kid_dp@test"):
    th = auth("teacher_dp@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth(email, "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    for i in range(msgs):
        await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": f"토끼 이야기 {i}"})
    return sh, book_id


async def test_ready_triggers_bible_prefetch_without_writing(client):
    sh, book_id = await _planned_book(client, msgs=3)  # 3개 → readyToWrite → 백그라운드 선생성
    store = get_store()
    bible = store.get_bible(book_id)
    assert bible is not None                         # Bible 선생성됨
    assert "_planHash" in bible.data
    assert store.get_book(book_id).status == "planning"  # 확정 전(버튼 전)


async def test_design_uses_prefetched_draft_instantly(client):
    sh, book_id = await _planned_book(client, msgs=3, email="kid_dp2@test")
    store = get_store()
    store.get_bible(book_id).data["_marker"] = "KEEP"  # 초안 표식(재빌드되면 사라짐)

    r = await client.post(f"/books/{book_id}/design", headers=sh)
    assert r.json()["status"] == "done"
    assert store.get_book(book_id).status == "writing"        # 확정 전이
    assert store.get_bible(book_id).data.get("_marker") == "KEEP"  # 초안 재사용(Pro 재호출 없음)


async def test_stale_draft_rebuilt_on_design(client):
    sh, book_id = await _planned_book(client, msgs=3, email="kid_dp3@test")
    store = get_store()
    store.get_bible(book_id).data["_marker"] = "OLD"

    # 대화를 더 이어가 설계 재료 변경 → 초안 stale.
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용도 나와요"})
    # 4번째 메시지 직후 백그라운드 재선생성으로 최신 해시 반영될 수 있음 → design 으로 최종 확정.
    r = await client.post(f"/books/{book_id}/design", headers=sh)
    assert r.json()["status"] == "done"
    bible = store.get_bible(book_id)
    assert bible.data["_planHash"].startswith("4:")  # 4개 메시지 반영된 최신 초안
