"""ReAct 오케스트레이터 테스트 — ScriptedPlanner 로 결정적 흐름·트레이스·일시정지 검증."""
from __future__ import annotations

from app.ai.gemini import GeminiClient
from app.ai.react import ScriptedPlanner, react_session, run_react
from app.ai.skills.base import Budget, SkillContext
from app.config import get_settings
from app.store.memory import InMemoryStore


def _ctx(store, session_id, budget=None):
    return SkillContext(
        store=store, gemini=GeminiClient(get_settings()), settings=get_settings(),
        session_id=session_id, book_id="book1", budget=budget or Budget(),
    )


async def test_scripted_flow_records_steps_and_finishes():
    store = InMemoryStore()
    store.upsert_bible("book1", {"title": "원제"})
    sess = store.create_ai_session("book1", "writer", "m")
    ctx = _ctx(store, sess.id)
    planner = ScriptedPlanner(
        [
            {"thought": "본문 생성", "skill": "generate_text", "args": {"prompt": "옛날에"}},
            {"thought": "Bible 갱신", "skill": "update_bible", "args": {"patch": {"world": {"tone": "밝은"}}}},
        ],
        result={"done": True},
    )
    res = await run_react(ctx, "한 챕터 쓰기", planner)
    assert res.status == "done"
    assert res.result == {"done": True}
    # 스텝 기록: generate_text, update_bible, finish = 3
    steps = store.list_ai_steps(sess.id)
    assert [s.skill for s in steps] == ["generate_text", "update_bible", "finish"]
    assert store.get_bible("book1").data["world"]["tone"] == "밝은"


async def test_react_session_lifecycle_done():
    store = InMemoryStore()
    planner = ScriptedPlanner([{"thought": "끝", "finish": True, "result": {"ok": 1}}])
    session, res = await react_session(
        store, GeminiClient(get_settings()), get_settings(),
        role="designer", goal="설계", planner=planner, book_id="book1",
    )
    assert res.status == "done"
    assert session.status == "done"
    assert session.ended_at


async def test_ask_user_pauses_awaiting():
    store = InMemoryStore()
    planner = ScriptedPlanner(
        [{"thought": "물어보기", "skill": "ask_user",
          "args": {"question": "주인공 이름은?", "choices": ["별이", "달이"], "allowText": True}}]
    )
    session, res = await react_session(
        store, GeminiClient(get_settings()), get_settings(),
        role="chat", goal="기획", planner=planner, book_id="book1",
    )
    assert res.status == "awaiting_user"
    assert res.pending["question"] == "주인공 이름은?"
    assert session.status == "awaiting_user"
    # ask_user 도 스텝으로 기록됨
    steps = store.list_ai_steps(session.id)
    assert steps[-1].skill == "ask_user"


async def test_max_steps_guard():
    store = InMemoryStore()
    sess = store.create_ai_session("book1", "writer", "m")
    ctx = _ctx(store, sess.id, budget=Budget(max_steps=1))
    # finish 없이 무한 액션을 주는 플래너
    class Loop(ScriptedPlanner):
        async def next_action(self, ctx, goal, history):
            return {"thought": "또", "skill": "check_safety", "args": {"text": "안녕"}}
    res = await run_react(ctx, "g", Loop([]), max_steps=1)
    assert res.status == "error"
    assert res.error in {"max_steps", "budget_exhausted"}


async def test_unknown_skill_errors():
    store = InMemoryStore()
    sess = store.create_ai_session("book1", "writer", "m")
    ctx = _ctx(store, sess.id)
    planner = ScriptedPlanner([{"thought": "x", "skill": "does_not_exist", "args": {}}])
    res = await run_react(ctx, "g", planner)
    assert res.status == "error"
    assert "unknown_skill" in res.error
