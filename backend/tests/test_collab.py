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


async def test_dialogue_edit_replaces_not_appends(client):
    """'두번째 문단 고쳐줘' → 새 문단 추가가 아니라 2번 문단 교체(05-기능수정 §02)."""
    sh, book_id = await _designed_book(client, email="kid_co7@test")
    await _collab(client, sh, book_id, 1, "토끼가 숲으로 갔어")        # seq1
    await _collab(client, sh, book_id, 1, "토끼가 폭포를 보았어")       # seq2
    before = (await client.get(f"/books/{book_id}/chapters/1/collab", headers=sh)).json()
    assert len(before["paragraphs"]) == 2
    r = (await _collab(client, sh, book_id, 1, "두번째 문단을 더 재미있게 고쳐줘")).json()
    assert r["kind"] == "paragraph"
    assert r["replacedSeq"] == 2
    after = (await client.get(f"/books/{book_id}/chapters/1/collab", headers=sh)).json()
    assert len(after["paragraphs"]) == 2  # 덧붙지 않음
    assert after["paragraphs"][1]["body"] == r["paragraph"]["body"]


async def test_direct_edit_paragraph(client):
    sh, book_id = await _designed_book(client, email="kid_co8@test")
    await _collab(client, sh, book_id, 1, "토끼가 숲으로 갔어")
    r = await client.patch(f"/books/{book_id}/chapters/1/paragraphs/1", headers=sh,
                           json={"body": "토끼가 맑은 시냇물을 따라 깡총깡총 뛰어갔어요."})
    assert r.status_code == 200
    assert r.json()["paragraph"]["body"].startswith("토끼가 맑은")
    state = (await client.get(f"/books/{book_id}/chapters/1/collab", headers=sh)).json()
    assert state["paragraphs"][0]["body"].startswith("토끼가 맑은")
    assert state["paragraphs"][0]["source"] == "revise"


async def test_reorder_paragraphs(client):
    sh, book_id = await _designed_book(client, email="kid_co9@test")
    await _collab(client, sh, book_id, 1, "토끼가 숲으로 갔어")        # seq1
    await _collab(client, sh, book_id, 1, "토끼가 폭포를 보았어")       # seq2
    first_body = (await client.get(f"/books/{book_id}/chapters/1/collab", headers=sh)).json()["paragraphs"][0]["body"]
    r = await client.post(f"/books/{book_id}/chapters/1/paragraphs/reorder", headers=sh,
                          json={"order": [2, 1]})
    assert r.status_code == 200
    paras = r.json()["paragraphs"]
    assert paras[1]["seq"] == 2 and paras[1]["body"] == first_body  # 1번이 2번으로


async def test_reorder_rejects_bad_order(client):
    sh, book_id = await _designed_book(client, email="kid_co10@test")
    await _collab(client, sh, book_id, 1, "토끼가 숲으로 갔어")
    r = await client.post(f"/books/{book_id}/chapters/1/paragraphs/reorder", headers=sh,
                          json={"order": [1, 2, 3]})  # 존재하지 않는 seq
    assert r.status_code == 409


async def test_collab_uses_skills_and_traces(client):
    """협업 한 턴이 write_paragraph·next_question 스킬로 실행되어 ai_steps 에 적재된다(§04)."""
    from app.ai.skills import SKILLS
    # 협업 스킬이 레지스트리에 등록됨.
    for name in ("write_paragraph", "revise_paragraph", "assess_flow", "assess_edit", "next_question"):
        assert name in SKILLS

    sh, book_id = await _designed_book(client, email="kid_co11@test")
    await _collab(client, sh, book_id, 1, "토끼가 숲으로 갔어")
    store = get_store()
    sessions = store.list_ai_sessions(role="writer")
    steps = [s for sess in sessions for s in store.list_ai_steps(sess.id)]
    skills_used = {s.skill for s in steps}
    assert "write_paragraph" in skills_used
    assert "next_question" in skills_used
