"""02 잔여 스킬 테스트 — persona_reply·tutor_answer·plan_interview·generate_choices·ai_council·generate_learning·notify (mock 결정성)."""
from __future__ import annotations

from app.ai.gemini import GeminiClient
from app.ai.skills import SKILLS, run_skill
from app.ai.skills.base import Budget, SkillContext
from app.config import get_settings
from app.store.memory import InMemoryStore


def _ctx(store, session_id=None):
    return SkillContext(
        store=store, gemini=GeminiClient(get_settings()), settings=get_settings(),
        session_id=session_id, book_id="book1", budget=Budget(),
    )


def test_extra_skills_registered():
    for name in [
        "persona_reply", "tutor_answer", "plan_interview",
        "generate_choices", "ai_council", "generate_learning", "notify",
    ]:
        assert name in SKILLS
    assert SKILLS["notify"].danger is True


async def test_persona_and_tutor():
    store = InMemoryStore()
    ctx = _ctx(store)
    pr = await run_skill(ctx, "persona_reply", {"character_name": "별이", "letter_body": "안녕"})
    assert "별이" in pr["reply"]
    ta = await run_skill(ctx, "tutor_answer", {"question": "증발이 뭐예요?"})
    assert ta["answer"]


async def test_plan_interview_and_choices():
    store = InMemoryStore()
    ctx = _ctx(store)
    pi = await run_skill(ctx, "plan_interview", {"history": ["용감한 토끼"], "latest": "씩씩해요"})
    assert pi["reply"]
    assert "readyToWrite" in pi
    ch = await run_skill(ctx, "generate_choices", {"context": "숲 갈림길", "n": 3})
    assert len(ch["choices"]) == 3


async def test_council_and_learning():
    store = InMemoryStore()
    store.upsert_bible("book1", {"events": [{"chapterIdx": 1, "objective": "증발"}]})
    ch = store.create_chapter("book1", 1, "free")
    store.update_chapter(ch.id, body="비가 증발했어요", char_count=8, words=["증발", "구름"])
    ctx = _ctx(store)
    co = await run_skill(ctx, "ai_council", {"topic": "이야기 방향"})
    assert co["consensus"]
    le = await run_skill(ctx, "generate_learning", {})
    assert "증발" in le["vocabTerms"]
    assert "증발" in le["objectives"]


async def test_notify_skill_creates():
    store = InMemoryStore()
    ctx = _ctx(store)
    obs = await run_skill(ctx, "notify", {"title": "테스트 알림", "is_broadcast": True})
    assert obs["id"]
    assert len(store.notifications) == 1
