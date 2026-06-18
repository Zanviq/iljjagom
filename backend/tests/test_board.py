"""학급 게시판(학생/15 §4 · 14) — 발표 등록·승인·반려·가시성·자동공개."""
from __future__ import annotations

from app.store import get_store
from tests.conftest import auth


async def _setup(client, *, student2: bool = False):
    th = auth("teacher_bd@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth("kid_bd@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    sh2 = None
    if student2:
        sh2 = auth("kid_bd2@test", "student")
        await client.post("/onboarding", headers=sh2, json={"role": "student", "classCode": code, "guardianConsent": True})
    return th, sh, sh2, class_id, book_id


def _mark_done(book_id, title="물의 모험"):
    get_store().update_book(book_id, status="done", title=title)


async def test_cannot_publish_unfinished_book(client):
    th, sh, _, class_id, book_id = await _setup(client)
    r = await client.post(f"/books/{book_id}/board-posts", headers=sh, json={"intro": "재밌어요"})
    assert r.status_code == 409  # 완성 전


async def test_publish_pending_then_teacher_approves(client):
    th, sh, sh2, class_id, book_id = await _setup(client, student2=True)
    _mark_done(book_id)
    created = (await client.post(f"/books/{book_id}/board-posts", headers=sh, json={"intro": "꼭 읽어줘"})).json()
    assert created["status"] == "pending"
    post_id = created["postId"]

    # 다른 학생: 아직 공개 전이라 목록에 안 보이고 상세도 403.
    other_list = (await client.get(f"/classes/{class_id}/board-posts", headers=sh2)).json()["posts"]
    assert all(p["id"] != post_id for p in other_list)
    assert (await client.get(f"/board-posts/{post_id}", headers=sh2)).status_code == 403

    # 교사: 전체(pending) 보임 → 승인.
    teacher_list = (await client.get(f"/classes/{class_id}/board-posts", headers=th)).json()["posts"]
    assert any(p["id"] == post_id for p in teacher_list)
    appr = (await client.post(f"/board-posts/{post_id}/approve", headers=th)).json()
    assert appr["status"] == "published"

    # 이제 다른 학생도 공개분으로 보인다.
    other_list2 = (await client.get(f"/classes/{class_id}/board-posts", headers=sh2)).json()["posts"]
    assert any(p["id"] == post_id for p in other_list2)
    assert (await client.get(f"/board-posts/{post_id}", headers=sh2)).status_code == 200


async def test_reject_then_resubmit(client):
    th, sh, _, class_id, book_id = await _setup(client)
    _mark_done(book_id)
    post_id = (await client.post(f"/books/{book_id}/board-posts", headers=sh, json={})).json()["postId"]
    rej = (await client.post(f"/board-posts/{post_id}/reject", headers=th, json={"note": "제목을 더 다듬어요"})).json()
    assert rej["status"] == "rejected" and rej["reviewNote"] == "제목을 더 다듬어요"

    # 재제출 → 같은 글이 pending 으로 초기화(검토 메모 비움).
    re = (await client.post(f"/books/{book_id}/board-posts", headers=sh, json={"intro": "고쳤어요"})).json()
    assert re["postId"] == post_id and re["status"] == "pending"
    view = (await client.get(f"/board-posts/{post_id}", headers=sh)).json()
    assert view["status"] == "pending" and view["reviewNote"] is None


async def test_auto_publish_classroom(client):
    th, sh, _, class_id, book_id = await _setup(client)
    _mark_done(book_id)
    get_store().get_classroom(class_id).board_auto_publish = True  # 학급 자동공개 토글(교사 제어는 P5)
    created = (await client.post(f"/books/{book_id}/board-posts", headers=sh, json={})).json()
    assert created["status"] == "published"  # 승인 없이 즉시 공개


async def test_snapshot_included(client):
    th, sh, _, class_id, book_id = await _setup(client)
    _mark_done(book_id, title="별빛 토끼")
    post_id = (await client.post(f"/books/{book_id}/board-posts", headers=sh, json={})).json()["postId"]
    view = (await client.get(f"/board-posts/{post_id}", headers=sh)).json()
    assert view["title"] == "별빛 토끼"
    assert "chapterCount" in view["snapshot"]
