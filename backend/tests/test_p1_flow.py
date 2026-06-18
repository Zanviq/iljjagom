"""P1 합의 경계(03-기능명세서 §9) 전체 시나리오 + 계약 검증."""
from __future__ import annotations

import json

from tests.conftest import auth


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"  # test 모드는 인메모리라도 degraded 아님
    assert body["storage"] == "in-memory"
    assert body["ai"] == "mock"
    assert body["env"] == "test"
    assert body["version"]


async def test_health_ready(client):
    # 테스트(인메모리)에서는 DB 핑을 건너뛰므로 항상 ready.
    r = await client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"]["db"] is True


async def test_me_needs_onboarding(client):
    r = await client.get("/me", headers=auth("kid@test", "student"))
    assert r.status_code == 200
    body = r.json()
    assert body["needsOnboarding"] is True
    assert body["role"] == "student"
    assert body["email"] == "kid@test"


async def test_unauthorized(client):
    r = await client.get("/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


async def test_admin_whitelist(client):
    r = await client.get("/me", headers=auth("admin@iljjagom.test", "student"))
    assert r.json()["role"] == "admin"
    assert r.json()["needsOnboarding"] is False


async def _teacher_makes_prompt(client):
    """교사 온보딩 → 학급 코드 확보 → 발제 1개 생성. (코드, classId, promptId) 반환."""
    th = auth("teacher@test", "teacher")
    r = await client.post(
        "/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False}
    )
    assert r.status_code == 200
    assert r.json()["role"] == "teacher"

    r = await client.get("/classes", headers=th)
    assert r.status_code == 200
    classes = r.json()["classes"]
    assert len(classes) == 1
    class_id = classes[0]["id"]
    code = classes[0]["code"]

    r = await client.post(
        f"/classes/{class_id}/prompts",
        headers=th,
        json={
            "topic": "물의 순환",
            "learningObjectives": ["증발·응결·강수 이해", "관련 어휘 5개"],
            "assessment": {"type": "quiz", "detail": "5문항"},
            "language": "ko",
        },
    )
    assert r.status_code == 201
    prompt = r.json()
    assert prompt["classId"] == class_id
    assert prompt["topic"] == "물의 순환"
    return code, class_id, prompt["id"]


async def test_me_class_fields(client):
    # 03 §4.2: 학생은 가입 학급의 classId/className 을 받고, 미가입·교사는 null.
    code, class_id, _ = await _teacher_makes_prompt(client)

    # 미가입 학생: null
    sh = auth("kid_solo@test", "student")
    me = (await client.get("/me", headers=sh)).json()
    assert me["classId"] is None
    assert me["className"] is None

    # 온보딩(학급 코드) 응답에 즉시 채워짐
    on = (await client.post(
        "/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True}
    )).json()
    assert on["classId"] == class_id
    assert on["className"] == "우리 반"

    # 이후 GET /me 에서도 동일
    me = (await client.get("/me", headers=sh)).json()
    assert me["classId"] == class_id
    assert me["className"] == "우리 반"

    # 교사는 학급을 만들어도 classId/className 은 null(학생 전용 진입점).
    th = auth("teacher@test", "teacher")
    tme = (await client.get("/me", headers=th)).json()
    assert tme["classId"] is None
    assert tme["className"] is None


async def test_list_books(client):
    # 03 §4.2 GET /books: 학생 자기 책만, 최근 활동 순, chaptersDone/updatedAt 포함.
    code, class_id, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_list@test", "student")
    await client.post(
        "/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True}
    )

    # 책 없을 때 빈 목록
    r = await client.get("/books", headers=sh)
    assert r.status_code == 200
    assert r.json()["books"] == []

    # 책 2권 생성
    await client.post("/books", headers=sh, json={"promptId": prompt_id})
    b2 = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]

    r = await client.get("/books", headers=sh)
    books_list = r.json()["books"]
    assert len(books_list) == 2
    item = books_list[0]
    for key in ("id", "title", "status", "chaptersDone", "totalChaptersPlanned", "updatedAt"):
        assert key in item
    assert item["status"] == "planning"
    assert item["chaptersDone"] == 0
    assert item["totalChaptersPlanned"] is None

    # b2 를 설계 + 1챕터 집필 → 최근 활동 순으로 맨 앞 + chaptersDone 증가
    await client.post(f"/books/{b2}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{b2}/design", headers=sh)
    await _read_sse(client, f"/books/{b2}/chapters/1/stream", sh)

    r = await client.get("/books", headers=sh)
    books_list = r.json()["books"]
    assert books_list[0]["id"] == b2  # 가장 최근 활동
    assert books_list[0]["chaptersDone"] == 1
    assert books_list[0]["totalChaptersPlanned"] == 6

    # 다른 학생은 이 책들을 보지 못한다(자기 책만).
    other = auth("kid_other@test", "student")
    await client.post("/onboarding", headers=other, json={"role": "student", "classCode": code, "guardianConsent": True})
    r = await client.get("/books", headers=other)
    assert r.json()["books"] == []


async def test_full_p1_vertical_slice(client):
    # 1. 교사: 발제 생성
    code, class_id, prompt_id = await _teacher_makes_prompt(client)

    # 2. 학생: 온보딩(학급 코드) → 책 생성
    sh = auth("kid@test", "student")
    r = await client.post(
        "/onboarding",
        headers=sh,
        json={"role": "student", "classCode": code, "guardianConsent": True, "grade": 4},
    )
    assert r.status_code == 200
    assert r.json()["needsOnboarding"] is False

    # 학생은 학급 발제를 볼 수 있다
    r = await client.get(f"/classes/{class_id}/prompts", headers=sh)
    assert r.status_code == 200
    assert len(r.json()["prompts"]) == 1

    r = await client.post("/books", headers=sh, json={"promptId": prompt_id})
    assert r.status_code == 201
    book = r.json()
    assert book["status"] == "planning"
    assert book["classId"] == class_id
    book_id = book["id"]

    # 3. 기획 대화 몇 번
    for msg in ["주인공은 용감한 토끼야", "숲속에 살아", "호기심이 많아"]:
        r = await client.post(
            f"/books/{book_id}/plan/messages", headers=sh, json={"message": msg}
        )
        assert r.status_code == 200
        reply = r.json()
        assert "reply" in reply
        assert "characterDraft" in reply
    assert reply["readyToWrite"] is True
    assert "용감함" in reply["characterDraft"]["traits"]

    # 4. 설계 → Bible 생성
    r = await client.post(f"/books/{book_id}/design", headers=sh)
    assert r.status_code == 202
    design = r.json()
    assert design["status"] == "done"
    assert design["totalChaptersPlanned"] == 6

    # 책 상태 writing 으로 전이 + 챕터 골격
    r = await client.get(f"/books/{book_id}", headers=sh)
    detail = r.json()
    assert detail["status"] == "writing"
    assert detail["totalChaptersPlanned"] == 6
    assert len(detail["chapters"]) == 6
    assert detail["chapters"][0]["mode"] == "free"
    assert detail["chapters"][-1]["mode"] == "guided"

    # 5. 1챕터 SSE 스트림
    events = await _read_sse(client, f"/books/{book_id}/chapters/1/stream", sh)
    types = [e[0] for e in events]
    assert types[0] == "meta"
    assert "token" in types
    assert types[-1] == "done"
    meta = events[0][1]
    assert meta["chapterIdx"] == 1
    done = events[-1][1]
    assert done["chapterIdx"] == 1
    assert done["nextChapterAvailable"] is True
    assert done["charCount"] > 0

    # 본문이 토큰을 이어 붙인 것과 일치하는지 (글자 단위 흐름 확인)
    body = "".join(e[1]["text"] for e in events if e[0] == "token")
    assert len(body) == done["charCount"]
    # 학생/08: 스트림 본문에 마크다운/장번호 머리말이 없다(정제됨).
    assert "**" not in body and "# " not in body
    assert not any(line.strip() in ("1장.", "1 장") for line in body.splitlines())

    # 단어 도움 최소판
    r = await client.get(
        f"/books/{book_id}/words", headers=sh, params={"term": "수증기"}
    )
    assert r.status_code == 200
    assert r.json()["term"] == "수증기"


async def _design_and_write_ch1(client, headers, prompt_id):
    """책 생성 → 기획 → design → 1챕터 집필. (book_id, 본문) 반환."""
    book_id = (await client.post("/books", headers=headers, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=headers, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=headers)
    events = await _read_sse(client, f"/books/{book_id}/chapters/1/stream", headers)
    body = "".join(e[1]["text"] for e in events if e[0] == "token")
    return book_id, body


async def test_design_records_ai_session_trace(client):
    # 관측: 설계(design) 흐름이 designer ai_session + 스텝을 기록한다.
    from app.store import get_store

    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_tr@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)

    store = get_store()
    sessions = store.list_ai_sessions(book_id=book_id)
    designer = [s for s in sessions if s.role == "designer"]
    assert designer, "designer 세션이 기록되어야 함"
    assert designer[0].status == "done"
    steps = store.list_ai_steps(designer[0].id)
    skills = [s.skill for s in steps]
    assert "design_outline" in skills
    assert "embed_store" in skills


async def test_resubscribe_serves_stored_body(client):
    # 첫 집필 후 재구독하면 저장본을 그대로 흘린다(글자 동일).
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_re@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id, body1 = await _design_and_write_ch1(client, sh, prompt_id)

    events2 = await _read_sse(client, f"/books/{book_id}/chapters/1/stream", sh)
    body2 = "".join(e[1]["text"] for e in events2 if e[0] == "token")
    assert body2 == body1  # 저장본 재전송(재생성 아님)


async def test_revise_chapter_reflected_on_restream(client):
    # 자유모드 수정요청(P2-2): revise 202 → 재구독 시 수정 반영된 저장본.
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_rev@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id, body1 = await _design_and_write_ch1(client, sh, prompt_id)

    r = await client.post(
        f"/books/{book_id}/chapters/1/revise",
        headers=sh,
        json={"instruction": "주인공을 더 씩씩하게 해줘"},
    )
    assert r.status_code == 202
    assert r.json()["status"] == "revising"

    events2 = await _read_sse(client, f"/books/{book_id}/chapters/1/stream", sh)
    body2 = "".join(e[1]["text"] for e in events2 if e[0] == "token")
    assert body2 != body1
    assert "주인공을 더 씩씩하게" in body2  # 수정 지시 반영


async def test_revise_requires_written_chapter(client):
    # 집필 전 챕터 수정요청은 409.
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_rev2@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    r = await client.post(
        f"/books/{book_id}/chapters/1/revise", headers=sh, json={"instruction": "더 밝게"}
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


async def test_revise_blocks_unsafe_instruction(client):
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_rev3@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id, _ = await _design_and_write_ch1(client, sh, prompt_id)
    r = await client.post(
        f"/books/{book_id}/chapters/1/revise",
        headers=sh,
        json={"instruction": "다 죽여버릴거야"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


async def test_learning_artifacts(client):
    # FR-S8~S12: 어휘/퀴즈/독후감/감정 곡선.
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_learn@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id, _ = await _design_and_write_ch1(client, sh, prompt_id)

    r = await client.get(f"/books/{book_id}/learning", headers=sh)
    assert r.status_code == 200
    body = r.json()
    assert {"vocab", "quiz", "essayBlanks", "emotion", "letterCharacters"} <= set(body)
    # 학생/11: emotion 은 입력 틀(labels + points[value/label=null]).
    assert body["emotion"]["labels"]
    assert body["emotion"]["points"][0]["chapterIdx"] == 1
    assert body["emotion"]["points"][0]["value"] is None
    assert len(body["quiz"]) >= 1
    # 학생/10: 정답 인덱스는 choices 범위 안의 유효 위치(고정 0 아님).
    for q in body["quiz"]:
        assert 0 <= q["answerIndex"] < len(q["choices"])
    assert len(body["essayBlanks"]) >= 1


async def test_letter_answered(client):
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_letter@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id, _ = await _design_and_write_ch1(client, sh, prompt_id)

    r = await client.post(
        f"/books/{book_id}/letters",
        headers=sh,
        json={"to": "주인공", "body": "안녕 주인공아, 너의 용기가 정말 멋져!"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "answered"
    assert r.json()["reply"]


async def test_letter_held_on_risk(client):
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_letter2@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id, _ = await _design_and_write_ch1(client, sh, prompt_id)

    r = await client.post(
        f"/books/{book_id}/letters",
        headers=sh,
        json={"to": "주인공", "body": "다 죽여버릴거야"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "held"
    assert r.json()["reply"] is None


async def test_letter_unknown_character(client):
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_letter3@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id, _ = await _design_and_write_ch1(client, sh, prompt_id)
    r = await client.post(
        f"/books/{book_id}/letters",
        headers=sh,
        json={"to": "없는인물", "body": "안녕하세요"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


async def test_rate_limit_letters(client):
    # 비용 가드레일: letters 한도(20/윈도) 초과 시 429 rate_limited.
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_rl@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id, _ = await _design_and_write_ch1(client, sh, prompt_id)

    last = None
    for _ in range(21):
        last = await client.post(
            f"/books/{book_id}/letters",
            headers=sh,
            json={"to": "주인공", "body": "안녕 주인공아!"},
        )
    assert last.status_code == 429
    assert last.json()["error"]["code"] == "rate_limited"


async def test_admin_usage(client):
    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_usage@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    await client.post("/books", headers=sh, json={"promptId": prompt_id})

    # 비관리자는 접근 불가.
    r = await client.get("/admin/usage", headers=sh)
    assert r.status_code == 403

    # 관리자(화이트리스트)는 집계 조회.
    admin = auth("admin@iljjagom.test", "student")
    r = await client.get("/admin/usage", headers=admin)
    assert r.status_code == 200
    body = r.json()
    assert body["users"]["total"] >= 2  # teacher + student
    assert body["books"]["total"] >= 1
    assert body["classrooms"] >= 1
    assert "open" in body["safetyFlags"]


async def test_guided_chapter_has_illustration_first(client):
    code, class_id, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid2@test", "student")
    await client.post(
        "/onboarding",
        headers=sh,
        json={"role": "student", "classCode": code, "guardianConsent": True},
    )
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)

    # 유도(guided) 챕터(4장)는 illustration/prompt 가 token 보다 먼저.
    events = await _read_sse(client, f"/books/{book_id}/chapters/4/stream", sh)
    types = [e[0] for e in events]
    assert types[0] == "meta"
    assert "illustration" in types
    assert "prompt" in types
    assert types.index("illustration") < types.index("token")
    assert types.index("prompt") < types.index("token")


async def test_teacher_dashboard(client):
    # FR-T2: 학급 학생별 진척 + 요약 집계. 담당 교사만.
    code, class_id, prompt_id = await _teacher_makes_prompt(client)

    # 학생 2명 가입, 1명만 책 생성·설계·1챕터 집필.
    s1 = auth("dash_s1@test", "student")
    s2 = auth("dash_s2@test", "student")
    await client.post("/onboarding", headers=s1, json={"role": "student", "classCode": code, "guardianConsent": True})
    await client.post("/onboarding", headers=s2, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id, _ = await _design_and_write_ch1(client, s1, prompt_id)

    th = auth("teacher@test", "teacher")
    r = await client.get(f"/classes/{class_id}/dashboard", headers=th)
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["studentCount"] == 2
    assert body["summary"]["booksStarted"] == 1
    rows = {row["studentEmail"]: row for row in body["students"]}
    assert rows["dash_s1@test"]["bookId"] == book_id
    assert rows["dash_s1@test"]["chaptersDone"] == 1
    assert rows["dash_s1@test"]["totalChapters"] == 6
    assert rows["dash_s2@test"]["bookId"] is None

    # 담당이 아닌 다른 교사는 접근 불가(403).
    other = auth("teacher_other@test", "teacher")
    await client.post("/onboarding", headers=other, json={"role": "teacher"})
    r = await client.get(f"/classes/{class_id}/dashboard", headers=other)
    assert r.status_code == 403


async def test_role_guard_student_cannot_make_prompt(client):
    sh = auth("kid@test", "student")
    r = await client.post(
        "/classes/some-id/prompts",
        headers=sh,
        json={"topic": "x", "learningObjectives": ["y"]},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


async def test_safety_blocks_bad_input(client):
    code, class_id, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid3@test", "student")
    await client.post(
        "/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True}
    )
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    r = await client.post(
        f"/books/{book_id}/plan/messages", headers=sh, json={"message": "다 죽여버릴거야"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


async def test_onboarding_invalid_code(client):
    sh = auth("kid4@test", "student")
    r = await client.post(
        "/onboarding", headers=sh, json={"role": "student", "classCode": "ZZZZZZ"}
    )
    assert r.status_code == 400


async def test_classcode_wildcard_rejected(client):
    # ilike 패턴 주입 시도(%)는 계약 레벨에서 차단되어야 한다.
    sh = auth("kid5@test", "student")
    for bad in ["%", "_", "ABC%23", "' OR '1"]:
        r = await client.post(
            "/onboarding", headers=sh, json={"role": "student", "classCode": bad}
        )
        assert r.status_code == 400, bad


async def test_reonboarding_cannot_change_role(client):
    # 권한 상승 차단: 학생으로 온보딩한 뒤 교사로 재온보딩 → 403.
    code, _, _ = await _teacher_makes_prompt(client)
    sh = auth("kid6@test", "student")
    r = await client.post(
        "/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True}
    )
    assert r.status_code == 200

    r = await client.post("/onboarding", headers=sh, json={"role": "teacher"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"

    # 같은 역할 재온보딩(동의 갱신 등)은 허용.
    r = await client.post(
        "/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True}
    )
    assert r.status_code == 200


async def test_illustration_placeholder_in_keyless_mode(client):
    # 키 없으면 삽화는 Storage 업로드 없이 placeholder 로 폴백(유도 챕터 illustration 이벤트).
    from app.storage import NoopStorage, get_storage

    assert isinstance(get_storage(), NoopStorage)
    assert get_storage().upload_illustration("x/1.png", b"data") is None

    code, _, prompt_id = await _teacher_makes_prompt(client)
    sh = auth("kid_ill@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "용감한 토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    events = await _read_sse(client, f"/books/{book_id}/chapters/4/stream", sh)
    illus = next(e[1] for e in events if e[0] == "illustration")
    assert illus["url"].startswith("https://placehold.co/")

    # 학생/07: placeholder 는 illustration_path 에 박제되지 않는다(다음에 실 삽화로 교체 가능).
    from app.store import get_store

    ch = get_store().get_chapter(book_id, 4)
    assert ch is not None and ch.illustration_path is None


def test_placeholder_has_no_identifier_code():
    # 학생/07: 폴백 placeholder 에 chN-해시 같은 식별자 코드가 박히지 않는다(중립·고정).
    from app.ai.imagen import _placeholder, is_placeholder_url

    url = _placeholder()
    assert is_placeholder_url(url)
    assert _placeholder() == url           # 호출마다 동일(식별자 없음)
    assert not is_placeholder_url("https://cdn.supabase.co/illustrations/x/1.png")


def test_dev_auth_secure_defaults():
    # 코드 기본값은 False(보안). (테스트 프로세스 env 는 DEV_AUTH=true 라 인스턴스가 아닌 필드 기본값을 본다.)
    from app.config import Settings

    assert Settings.model_fields["dev_auth"].default is False
    # 시크릿이 있으면 DEV_AUTH 가 켜져도 fail-closed.
    assert Settings(dev_auth=True, supabase_jwt_secret="x").dev_auth_enabled is False
    # 시크릿이 없고 명시적으로 켰을 때만 dev 토큰 허용.
    assert Settings(dev_auth=True, supabase_jwt_secret="").dev_auth_enabled is True
    assert Settings(dev_auth=False, supabase_jwt_secret="").dev_auth_enabled is False


async def _read_sse(client, url: str, headers: dict) -> list[tuple[str, dict]]:
    """SSE 응답을 (event, data) 목록으로 파싱."""
    events: list[tuple[str, dict]] = []
    async with client.stream("GET", url, headers=headers) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        event_name = None
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
                events.append((event_name, data))
            elif line.startswith(":"):
                continue  # 하트비트
    return events
