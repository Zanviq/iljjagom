"""총괄(Overseer) AI — 채팅→이동/책생성 액션, 세션 연속, 안전·동의 게이트, 관리자 트레이스."""
from __future__ import annotations

from app.ai.routes import is_allowed_route, route_for_book
from app.ai.sanitize import sanitize_reply
from tests.conftest import auth

ADMIN = "admin@iljjagom.test"


async def _setup_student(client, *, consent: bool = True, email: str = "kid_ov@test"):
    """교사·발제·학생(가입) 준비. (student_headers, class_id, code, prompt_id) 반환."""
    th = auth("teacher_ov@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(
        f"/classes/{class_id}/prompts", headers=th,
        json={"topic": "물의 순환", "learningObjectives": ["증발"], "assessment": {}},
    )
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth(email, "student")
    await client.post(
        "/onboarding", headers=sh,
        json={"role": "student", "classCode": code, "guardianConsent": consent},
    )
    return sh, class_id, code, prompt_id


# --- 라우트 화이트리스트(단위) ---

def test_route_whitelist():
    assert is_allowed_route("/home")
    assert is_allowed_route("/learn")
    assert is_allowed_route("/learn/quiz")
    assert is_allowed_route("/books/new")
    assert is_allowed_route("/books/new?promptId=abc-123")
    uid = "12345678-1234-1234-1234-123456789abc"
    assert is_allowed_route(f"/books/{uid}/plan")
    assert is_allowed_route(f"/books/{uid}/read")
    # 거부: 외부 URL·프로토콜·임의 경로·//.
    assert not is_allowed_route("https://evil.com")
    assert not is_allowed_route("//evil.com")
    assert not is_allowed_route("/admin/users")
    assert not is_allowed_route("/books/notauuid/plan")
    assert not is_allowed_route("")


def test_route_for_book():
    assert route_for_book("planning", "b1") == "/books/b1/plan"
    assert route_for_book("writing", "b1") == "/books/b1/read"
    assert route_for_book("done", "b1") == "/books/b1/read"


# --- 핵심 흐름 ---

async def test_start_new_book_flow(client):
    sh, class_id, code, prompt_id = await _setup_student(client)
    r = await client.post("/ai/overseer/messages", headers=sh, json={"message": "책 쓰고 싶어"})
    assert r.status_code == 200
    data = r.json()
    assert data["sessionId"]
    assert "물의 순환" in data["reply"]
    assert len(data["actions"]) == 1
    action = data["actions"][0]
    assert action["type"] == "navigate"
    assert action["to"].startswith("/books/") and action["to"].endswith("/plan")
    assert action["label"] == "책 만들러 가기"

    # 책이 실제로 생성됐다(내 책 목록).
    books = (await client.get("/books", headers=sh)).json()["books"]
    assert len(books) == 1


async def test_session_continuity(client):
    sh, *_ = await _setup_student(client, email="kid_cont@test")
    r1 = await client.post("/ai/overseer/messages", headers=sh, json={"message": "안녕"})
    sid = r1.json()["sessionId"]

    r2 = await client.post(
        "/ai/overseer/messages", headers=sh,
        json={"message": "진행 얼마나 됐어?", "sessionId": sid},
    )
    assert r2.json()["sessionId"] == sid  # 같은 세션 이어가기

    # 관리자 트레이스: 스텝이 두 턴에 걸쳐 누적(idx 연속).
    ah = auth(ADMIN, "admin")
    detail = (await client.get(f"/ai/sessions/{sid}", headers=ah)).json()
    idxs = [s["idx"] for s in detail["steps"]]
    assert idxs == sorted(idxs) and len(set(idxs)) == len(idxs)  # 중복 없이 증가
    assert len(idxs) >= 8  # 턴당 read 3 + finish 1 이상


async def test_open_existing_book(client):
    sh, class_id, code, prompt_id = await _setup_student(client, email="kid_open@test")
    await client.post("/books", headers=sh, json={"promptId": prompt_id})
    r = await client.post("/ai/overseer/messages", headers=sh, json={"message": "이어서 읽을래"})
    data = r.json()
    assert len(data["actions"]) == 1
    assert data["actions"][0]["to"].startswith("/books/")


async def test_progress_info_no_action(client):
    sh, class_id, code, prompt_id = await _setup_student(client, email="kid_prog@test")
    await client.post("/books", headers=sh, json={"promptId": prompt_id})
    r = await client.post("/ai/overseer/messages", headers=sh, json={"message": "내 책 진행 얼마나 했어?"})
    data = r.json()
    assert data["actions"] == []
    assert "권" in data["reply"]


# --- 학생/16: 스킬 데이터 합성·예고/이모지 제거·반복 차단 ---

def test_sanitize_reply_strips_emoji_and_markdown():
    assert sanitize_reply("알려줄게! 😊") == "알려줄게!"
    assert sanitize_reply("**굵게** `코드` # 제목") == "굵게 코드 제목"
    assert sanitize_reply("- 첫째\n- 둘째") == "첫째 둘째"
    assert sanitize_reply("줄1\n줄2  \t 공백") == "줄1 줄2 공백"


async def test_activity_query_returns_real_data_not_teaser(client):
    # "지금까지 내가 한거 알려줘" → 예고가 아니라 실제 책 수·진행 장수가 담긴 답.
    sh, class_id, code, prompt_id = await _setup_student(client, email="kid_act@test")
    await client.post("/books", headers=sh, json={"promptId": prompt_id})
    r = await client.post(
        "/ai/overseer/messages", headers=sh, json={"message": "지금까지 내가 한거 알려줘"}
    )
    data = r.json()
    reply = data["reply"]
    assert data["actions"] == []
    assert "권" in reply
    assert any(c.isdigit() for c in reply)        # 실제 수치 포함
    assert "알려줄게" not in reply and "알려드릴게" not in reply  # 예고 아님


async def test_no_emoji_in_reply(client):
    sh, *_ = await _setup_student(client, email="kid_noemoji@test")
    r = await client.post("/ai/overseer/messages", headers=sh, json={"message": "안녕"})
    reply = r.json()["reply"]
    assert sanitize_reply(reply) == reply  # 정제해도 변화 없음(이모지·마크다운 부재)


async def test_repeated_question_no_teaser_loop(client):
    # 같은 질문을 두 번 — 둘 다 데이터 답이고, "알려줄게" 예고 루프가 없다.
    sh, class_id, code, prompt_id = await _setup_student(client, email="kid_loop@test")
    await client.post("/books", headers=sh, json={"promptId": prompt_id})
    sid = None
    for _ in range(2):
        body = {"message": "지금까지 한 거 알려줘"}
        if sid:
            body["sessionId"] = sid
        d = (await client.post("/ai/overseer/messages", headers=sh, json=body)).json()
        sid = d["sessionId"]
        assert "알려줄게" not in d["reply"]
        assert any(c.isdigit() for c in d["reply"])


# --- 안전 / 동의 게이트 ---

async def test_safety_gate_blocks_with_gentle_reply(client):
    sh, *_ = await _setup_student(client, email="kid_safe@test")
    from app.store import get_store

    r = await client.post("/ai/overseer/messages", headers=sh, json={"message": "죽고 싶어"})
    assert r.status_code == 200  # 하드 에러가 아니라 부드러운 안내
    assert r.json()["actions"] == []
    # 정서 위험 → safety_flag 기록(source=overseer).
    flags = [f for f in get_store().list_safety_flags() if f.source == "overseer"]
    assert len(flags) >= 1


async def test_guardian_consent_required(client):
    sh, *_ = await _setup_student(client, consent=False, email="kid_noconsent@test")
    r = await client.post("/ai/overseer/messages", headers=sh, json={"message": "책 쓰고 싶어"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "consent_required"


# --- 관리자 트레이스 / 소유권 ---

async def test_session_listed_with_user_for_admin(client):
    sh, *_ = await _setup_student(client, email="kid_trace@test")
    sid = (await client.post("/ai/overseer/messages", headers=sh, json={"message": "안녕"})).json()["sessionId"]

    ah = auth(ADMIN, "admin")
    sessions = (await client.get("/ai/sessions?role=overseer", headers=ah)).json()["sessions"]
    mine = next(s for s in sessions if s["id"] == sid)
    assert mine["role"] == "overseer"
    assert mine["userEmail"] == "kid_trace@test"
    assert mine["userId"]


async def test_foreign_session_id_starts_new(client):
    sh_a, class_id, code, prompt_id = await _setup_student(client, email="kid_a@test")
    sid_a = (await client.post("/ai/overseer/messages", headers=sh_a, json={"message": "안녕"})).json()["sessionId"]

    # 다른 학생(같은 학급·동의 가입)이 A 의 sessionId 를 들고 와도 재개되지 않고 새 세션이 열린다.
    sh_b = auth("kid_b@test", "student")
    await client.post(
        "/onboarding", headers=sh_b,
        json={"role": "student", "classCode": code, "guardianConsent": True},
    )
    r_b = await client.post(
        "/ai/overseer/messages", headers=sh_b,
        json={"message": "안녕", "sessionId": sid_a},
    )
    assert r_b.status_code == 200
    assert r_b.json()["sessionId"] != sid_a
