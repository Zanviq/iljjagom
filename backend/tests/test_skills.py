"""스킬 레지스트리 + 핵심 스킬 계약 테스트(mock 결정성).

설계: 03-추가기능/02. SkillContext 트레이스(ai_steps/token_usage)도 검증.
"""
from __future__ import annotations

import pytest

from app.ai.gemini import GeminiClient
from app.ai.skills import SKILLS, SkillError, run_skill, skill_catalog, validate_args
from app.ai.skills.base import Budget, SkillContext
from app.config import get_settings
from app.store.memory import InMemoryStore


def _ctx(store: InMemoryStore, session_id: str | None = None) -> SkillContext:
    return SkillContext(
        store=store,
        gemini=GeminiClient(get_settings()),
        settings=get_settings(),
        session_id=session_id,
        book_id="book1",
        budget=Budget(max_steps=10, max_tokens=100_000),
    )


def test_registry_collects_core_skills():
    for name in [
        "generate_text", "retrieve_context", "update_bible",
        "generate_image", "check_safety", "verify_objective", "summarize",
    ]:
        assert name in SKILLS, f"{name} 미수집"
    cat = skill_catalog()
    names = {c["name"] for c in cat}
    assert "generate_text" in names
    # danger 표시 확인
    assert SKILLS["update_bible"].danger is True
    assert SKILLS["generate_text"].danger is False


def test_validate_args_required_and_type():
    skill = SKILLS["generate_text"]
    with pytest.raises(SkillError):
        validate_args(skill, {})  # prompt 누락
    with pytest.raises(SkillError):
        validate_args(skill, {"prompt": 123})  # 타입 불일치
    validate_args(skill, {"prompt": "안녕", "role": "writer"})  # OK


async def test_generate_text_mock_and_trace():
    store = InMemoryStore()
    sess = store.create_ai_session("book1", "writer", "m")
    ctx = _ctx(store, sess.id)
    obs = await run_skill(ctx, "generate_text", {"prompt": "옛날 옛적에"}, thought="본문 시작")
    assert obs["text"].startswith("[mock:")
    # 트레이스 기록: ai_steps 1개 + token_usage 1개
    steps = store.list_ai_steps(sess.id)
    assert len(steps) == 1
    assert steps[0].skill == "generate_text"
    assert steps[0].thought == "본문 시작"
    assert steps[0].tokens_in > 0
    assert store.token_usage_summary()["calls"] == 1


async def test_update_bible_merges():
    store = InMemoryStore()
    store.upsert_bible("book1", {"title": "원제", "world": {"tone": "밝은"}})
    ctx = _ctx(store)
    obs = await run_skill(ctx, "update_bible", {"patch": {"world": {"setting": "숲"}, "title": "새제목"}})
    assert obs["ok"] is True
    data = store.get_bible("book1").data
    assert data["title"] == "새제목"
    assert data["world"] == {"tone": "밝은", "setting": "숲"}  # 깊은 병합


async def test_check_safety_blocks_and_risk():
    store = InMemoryStore()
    ctx = _ctx(store)
    bad = await run_skill(ctx, "check_safety", {"text": "죽여 버릴거야"})
    assert bad["ok"] is False
    assert bad["severity"] == "high"
    ok = await run_skill(ctx, "check_safety", {"text": "오늘은 즐거운 날이야"})
    assert ok["ok"] is True


async def test_verify_objective():
    store = InMemoryStore()
    ctx = _ctx(store)
    obs = await run_skill(
        ctx, "verify_objective",
        {"body": "오늘은 분수를 배웠어요.", "objectives": ["분수", "소수"]},
    )
    assert obs["met"] == ["분수"]
    assert obs["missing"] == ["소수"]
    assert obs["allMet"] is False


async def test_summarize_mock_deterministic():
    store = InMemoryStore()
    ctx = _ctx(store)
    obs = await run_skill(ctx, "summarize", {"text": "첫 문장입니다.\n둘째 문장.", "max_len": 100})
    assert obs["summary"] == "첫 문장입니다."


async def test_retrieve_context_uses_book_chunks():
    store = InMemoryStore()
    gem = GeminiClient(get_settings())
    # 청크 적재(임베딩 mock 결정적)
    emb = await gem.embed("주인공은 용감하다")
    store.add_chunk("book1", None, "주인공은 용감하다", emb)
    ctx = _ctx(store)
    obs = await run_skill(ctx, "retrieve_context", {"query": "주인공", "k": 3})
    assert "주인공" in obs["context"]


async def test_unknown_skill_raises():
    store = InMemoryStore()
    ctx = _ctx(store)
    with pytest.raises(SkillError):
        await run_skill(ctx, "nope", {})
