"""ai_council — 여러 역할 페르소나(설계자·교사·편집자)가 안을 비평·합의. 03-추가기능/02."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext, estimate_tokens

_PERSONAS = ["설계자", "교사", "편집자"]


class AiCouncil(Skill):
    name = "ai_council"
    description = "여러 역할(설계자·교사·편집자)이 초안을 비평하고 합의안을 도출한다."
    input_schema = {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "drafts": {"type": "array"},
        },
        "required": ["topic"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        topic: str = args["topic"]
        drafts: list = list(args.get("drafts") or [])
        if ctx.gemini.mock:
            return {
                "consensus": f"'{topic}'에 대해 세 역할이 핵심을 유지하기로 합의했어요.",
                "dissent": [],
                "personas": _PERSONAS,
            }
        model = ctx.model_for("designer")
        draft_text = "\n".join(f"- {d}" for d in drafts) or "(초안 없음)"
        prompt = (
            "너는 어린이 책 제작 회의를 진행한다. 설계자·교사·편집자 관점에서 아래 주제와 초안을 "
            "비평하고 한 문장 합의안을 제시한다.\n"
            f"주제: {topic}\n초안:\n{draft_text}\n\n합의안:"
        )
        consensus = (await ctx.gemini.generate_text(model, prompt)).strip()
        ctx.log_tokens(model, estimate_tokens(topic + draft_text), estimate_tokens(consensus))
        return {"consensus": consensus, "dissent": [], "personas": _PERSONAS}
