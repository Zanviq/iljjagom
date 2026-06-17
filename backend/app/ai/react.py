"""ReAct 오케스트레이터 — thought → skill → observation 반복으로 목표 달성.

설계: 03-추가기능/02 §4. 각 반복을 ai_steps 에 기록(SkillContext.emit), LLM/이미지 호출은
token_usage 에 기록(SkillContext.log_tokens). budget·max_steps 로 폭주 방지.

플래너 2종:
- ScriptedPlanner: 고정 액션 시퀀스(기존 4계층 재구성·테스트). mock/real 동일하게 결정적.
- LLMPlanner: 실 Gemini 가 다음 액션을 JSON 으로 결정(엄격 프로토콜). mock 이면 즉시 finish.

ask_user 액션은 세션을 awaiting_user 로 두고 일시정지(재개는 answer 엔드포인트, 2C).
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.ai.gemini import GeminiClient
from app.ai.skills import SKILLS, SkillError, run_skill, skill_catalog
from app.ai.skills.base import Budget, SkillContext, estimate_tokens
from app.config import Settings
from app.store.base import Store
from app.store.records import AiSessionRecord

ASK_USER = "ask_user"


@dataclass
class ReactResult:
    status: str  # done | awaiting_user | error
    result: dict[str, Any] = field(default_factory=dict)
    steps: int = 0
    pending: dict[str, Any] | None = None  # ask_user 질문(awaiting_user 일 때)
    error: str | None = None


# --- 플래너 ---


class Planner(ABC):
    @abstractmethod
    async def next_action(
        self, ctx: SkillContext, goal: str, history: list[dict]
    ) -> dict[str, Any]:
        """다음 액션 반환: {thought, skill, args} | {thought, finish, result}."""
        ...


class ScriptedPlanner(Planner):
    """고정 액션 시퀀스를 순서대로 수행하고 끝에 finish. 결정적."""

    def __init__(self, actions: list[dict[str, Any]], result: dict[str, Any] | None = None) -> None:
        self._actions = list(actions)
        self._i = 0
        self._result = result or {}

    async def next_action(self, ctx, goal, history):
        if self._i >= len(self._actions):
            return {"thought": "계획 완료", "finish": True, "result": self._result}
        action = self._actions[self._i]
        self._i += 1
        return action


class LLMPlanner(Planner):
    """실 Gemini 가 catalog 를 보고 다음 액션을 JSON 으로 결정. mock 이면 즉시 finish."""

    def __init__(self, allowed_skills: list[str] | None = None, role: str = "writer") -> None:
        self.allowed = allowed_skills
        self.role = role

    async def next_action(self, ctx, goal, history):
        if ctx.gemini.mock:
            return {"thought": "mock 종료", "finish": True, "result": {}}
        catalog = skill_catalog(self.allowed)
        model = ctx.model_for(self.role)
        prompt = _decision_prompt(goal, catalog, history)
        raw = await ctx.gemini.generate_text(model, prompt)
        ctx.log_tokens(model, estimate_tokens(prompt), estimate_tokens(raw))
        return _parse_action(raw)


def _decision_prompt(goal: str, catalog: list[dict], history: list[dict]) -> str:
    tools = "\n".join(
        f"- {c['name']}: {c['description']} (args: {list((c['input_schema'].get('properties') or {}).keys())})"
        for c in catalog
    )
    hist = "\n".join(
        f"{i}. {h.get('skill')} -> {json.dumps(h.get('observation', {}), ensure_ascii=False)[:200]}"
        for i, h in enumerate(history)
    )
    return (
        "너는 도구를 골라 목표를 달성하는 에이전트다. 다음 중 하나만 JSON 으로 출력한다.\n"
        '액션: {"thought": "...", "skill": "도구이름", "args": {..}}\n'
        '종료: {"thought": "...", "finish": true, "result": {..}}\n'
        "JSON 외 텍스트 금지.\n\n"
        f"목표: {goal}\n\n사용 가능한 도구:\n{tools}\n\n지금까지 기록:\n{hist or '(없음)'}\n\n다음 액션 JSON:"
    )


def _parse_action(raw: str) -> dict[str, Any]:
    t = raw.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.endswith("```"):
            t = t[:-3]
        if t.startswith("json"):
            t = t[4:]
    try:
        data = json.loads(t.strip())
        if not isinstance(data, dict):
            raise ValueError
        return data
    except (json.JSONDecodeError, ValueError, TypeError):
        # 파싱 실패 → 안전하게 종료(폭주 방지).
        return {"thought": "파싱 실패로 종료", "finish": True, "result": {"parse_error": True}}


# --- 오케스트레이터 ---


async def run_react(
    ctx: SkillContext,
    goal: str,
    planner: Planner,
    max_steps: int | None = None,
) -> ReactResult:
    """ctx.session_id 세션 아래에서 ReAct 루프 실행. 세션 생성/종료는 호출자 또는 react_session."""
    limit = max_steps if max_steps is not None else ctx.budget.max_steps
    history: list[dict] = []
    for _ in range(limit):
        if ctx.budget.exhausted():
            return ReactResult(status="error", error="budget_exhausted", steps=len(history))
        action = await planner.next_action(ctx, goal, history)
        if action.get("finish"):
            ctx.emit(action.get("thought"), "finish", {}, action.get("result", {}))
            return ReactResult(status="done", result=action.get("result", {}), steps=len(history))
        skill_name = action.get("skill")
        args = action.get("args", {}) or {}
        thought = action.get("thought")
        if skill_name == ASK_USER:
            # 일시정지: 질문을 기록하고 awaiting_user 로 종료. 재개는 answer 엔드포인트.
            ctx.emit(thought, ASK_USER, args, {"awaiting": True})
            return ReactResult(status="awaiting_user", pending=args, steps=len(history))
        if skill_name not in SKILLS:
            return ReactResult(status="error", error=f"unknown_skill:{skill_name}", steps=len(history))
        try:
            obs = await run_skill(ctx, skill_name, args, thought=thought)
        except SkillError as e:
            return ReactResult(status="error", error=str(e), steps=len(history))
        history.append({"skill": skill_name, "args": args, "observation": obs})
    return ReactResult(status="error", error="max_steps", steps=len(history))


async def react_session(
    store: Store,
    gemini: GeminiClient,
    settings: Settings,
    *,
    role: str,
    goal: str,
    planner: Planner,
    book_id: str | None = None,
    user_id: str | None = None,
    model: str | None = None,
    budget: Budget | None = None,
    max_steps: int | None = None,
) -> tuple[AiSessionRecord, ReactResult]:
    """세션 생성 → ReAct 실행 → 세션 종료(done/awaiting_user/error). (세션, 결과) 반환."""
    session = store.create_ai_session(book_id, role, model)
    ctx = SkillContext(
        store=store,
        gemini=gemini,
        settings=settings,
        session_id=session.id,
        book_id=book_id,
        user_id=user_id,
        budget=budget or Budget(),
    )
    result = await run_react(ctx, goal, planner, max_steps=max_steps)
    if result.status == "awaiting_user":
        store.update_ai_session(session.id, status="awaiting_user")
    elif result.status == "done":
        from app.util import now_iso

        store.update_ai_session(session.id, status="done", ended_at=now_iso())
    else:
        from app.util import now_iso

        store.update_ai_session(
            session.id, status="error", error=result.error, ended_at=now_iso()
        )
    refreshed = store.get_ai_session(session.id) or session
    return refreshed, result
