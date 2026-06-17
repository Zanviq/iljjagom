"""generate_text — 문장/본문 생성(집필 핵심). 03-추가기능/02 카탈로그."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class GenerateText(Skill):
    name = "generate_text"
    description = "주어진 프롬프트로 자연스러운 한국어 문장/본문을 생성한다. 집필의 핵심 능력."
    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "role": {"type": "string"},  # writer|editor|chat|designer (모델 선택)
        },
        "required": ["prompt"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        prompt: str = args["prompt"]
        role: str = args.get("role", "writer")
        model = ctx.model_for(role)
        text = await ctx.gemini.generate_text(model, prompt)
        ctx.log_tokens(model, estimate_tokens(prompt), estimate_tokens(text))
        return {"text": text, "model": model}
