"""자유집필 협업(학생/15 §2) — 문단 생성·지도·상태복원·완료 게이트·free 한정."""
from __future__ import annotations

from app.services.collab import COLLAB_TARGET_PARAGRAPHS
from app.store import get_store
from tests.conftest import auth


async def _designed_book(client, email="kid_co@test"):
    th = auth("teacher_co@test", "teacher")
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
    return sh, book_id


async def _collab(client, sh, book_id, idx, message, accept=False):
    r = await client.post(f"/books/{book_id}/chapters/{idx}/collab", headers=sh,
                          json={"message": message, "accept": accept})
    return r


async def test_first_turn_generates_paragraph(client):
    sh, book_id = await _designed_book(client)
    r = await _collab(client, sh, book_id, 1, "토끼가 숲으로 길을 나섰어")
    assert r.status_code == 200
    d = r.json()
    assert d["kind"] == "paragraph"
    assert d["paragraph"]["seq"] == 1 and d["paragraph"]["body"]
    assert d["question"]            # 진행 질문 동반
    assert d["chapterComplete"] is False
    # GET /books 의 chapters[].paragraphCount 반영
    detail = (await client.get(f"/books/{book_id}", headers=sh)).json()
    ch1 = next(c for c in detail["chapters"] if c["idx"] == 1)
    assert ch1["paragraphCount"] == 1


async def test_offtopic_gets_coaching_then_accept_generates(client):
    sh, book_id = await _designed_book(client, email="kid_co2@test")
    await _collab(client, sh, book_id, 1, "토끼가 숲으로 갔어")          # para1(토끼/숲)
    coach = (await _collab(client, sh, book_id, 1, "갑자기 우주선이 나타났어")).json()
    assert coach["kind"] == "coaching"
    assert coach["coaching"]["text"] and coach["paragraph"] is None
    # 제안 수용 → 생성.
    acc = (await _collab(client, sh, book_id, 1, "그래 토끼는 계속 걸었어", accept=True)).json()
    assert acc["kind"] == "paragraph"


async def test_state_restores_paragraphs_and_turns(client):
    sh, book_id = await _designed_book(client, email="kid_co3@test")
    await _collab(client, sh, book_id, 1, "토끼가 숲으로 갔어")
    state = (await client.get(f"/books/{book_id}/chapters/1/collab", headers=sh)).json()
    assert len(state["paragraphs"]) == 1
    assert state["paragraphs"][0]["seq"] == 1
    # 턴: 학생 1 + writer(문단) 1 + writer(질문) 1
    roles = [t["role"] for t in state["turns"]]
    assert roles.count("student") == 1 and roles.count("writer") >= 2


async def test_chapter_complete_gate(client):
    sh, book_id = await _designed_book(client, email="kid_co4@test")
    last = None
    for i in range(COLLAB_TARGET_PARAGRAPHS):
        last = (await _collab(client, sh, book_id, 1, f"토끼가 {i}번째 길을 걸었어")).json()
    assert last["chapterComplete"] is True
    assert last["question"] is None  # 완료 시 진행 질문 없음
    # body 재조립: 문단 수만큼 채워짐.
    store = get_store()
    ch = store.get_chapter(book_id, 1)
    assert ch.char_count > 0 and ch.body.count("\n\n") == COLLAB_TARGET_PARAGRAPHS - 1


async def test_collab_rejected_on_guided_chapter(client):
    sh, book_id = await _designed_book(client, email="kid_co5@test")
    r = await _collab(client, sh, book_id, 4, "전개를 바꿔줘")  # idx4 = guided
    assert r.status_code == 409  # conflict


async def test_emotional_risk_records_flag(client):
    sh, book_id = await _designed_book(client, email="kid_co6@test")
    await _collab(client, sh, book_id, 1, "죽고 싶어")
    flags = [f for f in get_store().list_safety_flags() if f.source == "collab"]
    assert len(flags) >= 1
