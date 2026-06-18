"""plan_interview — 기획 인터뷰 질문/인물카드 누적. 03-추가기능/02 카탈로그."""
from __future__ import annotations

from typing import Any

from app.ai import chat
from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class PlanInterview(Skill):
    name = "plan_interview"
    description = "기획 인터뷰 — 인물·배경·분위기 질문을 던지고 인물 카드를 누적한다(결말 비공개)."
    input_schema = {
        "type": "object",
        "properties": {
            "history": {"type": "array"},
            "latest": {"type": "string"},
        },
        "required": ["latest"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        history: list[str] = list(args.get("history") or [])
        latest: str = args["latest"]
        reply = await chat.interview_reply(ctx.gemini, history + [latest], latest)
        ctx.log_tokens(ctx.model_for("chat"), estimate_tokens(latest), estimate_tokens(reply.reply))
        return {
            "reply": reply.reply,
            "traits": reply.character_draft.traits,
            "readyToWrite": reply.ready_to_write,
        }
