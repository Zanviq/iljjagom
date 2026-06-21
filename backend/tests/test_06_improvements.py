"""06 기능개선 회귀 — 자유모드 간섭 제어·학습결과 캐시 제외·이어가기 시작 장·이미지 프롬프트."""
from __future__ import annotations

from app.ai import chat
from app.ai.gemini import GeminiClient
from app.deps import CurrentUser
from app.services import events
from app.store import get_store


def _user(uid: str, role: str = "student") -> CurrentUser:
    return CurrentUser(id=uid, email=f"{uid}@x", role=role, profile=None, needs_onboarding=False)


async def test_assess_flow_off_always_generates():
    g = GeminiClient()  # mock
    # 흐름이 끊기는 의도라도 off 면 코칭 없이 generate(간섭 0, 06 §5).
    d = await chat.assess_flow(
        g, {}, "토끼가 숲을 걸었어요", "증발", "갑자기 우주선이 나타났다", coaching_level="off"
    )
    assert d["action"] == "generate"


async def test_assess_flow_light_coaches_only_flow_break():
    g = GeminiClient()  # mock
    # 직전 문단과 공통 내용어가 있으면(흐름 OK) generate.
    ok = await chat.assess_flow(
        g, {}, "토끼가 숲을 걸었어요", "증발", "토끼가 숲에서 친구를 만났어요", coaching_level="light"
    )
    assert ok["action"] == "generate"
    # 흐름이 명백히 끊기면 light 에서도 coach(흐름만).
    brk = await chat.assess_flow(
        g, {}, "토끼가 숲을 걸었어요", "증발", "전혀상관없는단어들", coaching_level="light"
    )
    assert brk["action"] == "coach" and "흐름" in brk["reasons"]


def test_resolve_coaching_level_default_light():
    from app.services.policy import resolve_coaching_level

    store = get_store()
    assert resolve_coaching_level(store, None) == "light"  # 기본값


def test_class_settings_coaching_level_validation():
    from app.errors import ApiError
    from app.models.schemas import ClassSettingsPut
    from app.services import teacher

    store = get_store()
    user = _user("t-coach", "teacher")
    cls = store.create_classroom("t-coach", "반", "CODECODE")
    # 잘못된 값 거부.
    try:
        teacher.put_class_settings(store, user, cls.id, ClassSettingsPut(value={"coachingLevel": "wrong"}))
        assert False, "잘못된 coachingLevel 이 통과됨"
    except ApiError as e:
        assert e.code == "validation_error"
    # 허용값 통과 + 저장.
    res = teacher.put_class_settings(store, user, cls.id, ClassSettingsPut(value={"coachingLevel": "off"}))
    assert res.value.get("coachingLevel") == "off"


def test_learning_results_excludes_cache_types():
    store = get_store()
    book = store.create_book("kid-06", None, None)
    store.add_learning_artifact(book.id, "quiz", {"a": 1})
    store.add_learning_artifact(book.id, "learning_set", {"cache": True})
    store.add_learning_artifact(book.id, "mid_activity", {"cache": True})
    user = _user("kid-06")
    res = events.list_learning_results(store, user, book.id)
    types = {r.type for r in res.results}
    assert "quiz" in types
    assert "learning_set" not in types and "mid_activity" not in types


def test_book_detail_has_current_chapter_idx():
    from app.services import books

    store = get_store()
    book = store.create_book("kid-06b", None, None)  # planning
    user = _user("kid-06b")
    detail = books.get_book_detail(store, user, book.id)
    # planning 단계는 1장(plan)부터.
    assert detail.current_chapter_idx == 1


def test_image_prompt_forbids_text():
    from app.ai.imagen import _build_image_prompt

    p = _build_image_prompt("토끼가 숲을 걸어요", [{"name": "토끼"}])
    assert "글자" in p and "No text" in p  # 텍스트 금지 지시 포함(06 §1)
