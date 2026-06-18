"""generate_choices — 분기/추천 선택지 생성. 03-추가기능/02 카탈로그."""
from __future__ import annotations

import json
from typing import Any

from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class GenerateChoices(Skill):
    name = "generate_choices"
    description = "맥락에 맞는 선택지 n개를 만든다(분기·추천). 결말은 누설하지 않는다."
    input_schema = {
        "type": "object",
        "properties": {
            "context": {"type": "string"},
            "n": {"type": "integer"},
        },
        "required": ["context"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        context: str = args["context"]
        n = max(2, min(5, int(args.get("n", 3))))
        if ctx.gemini.mock:
            return {"choices": [f"선택 {i + 1}" for i in range(n)]}
        model = ctx.model_for("chat")
        prompt = (
            f"다음 맥락에 이어질 어린이용 선택지 {n}개를 JSON 배열(문자열만)로 만든다. "
            "결말은 드러내지 않는다. JSON 배열만 출력.\n"
            f"맥락: {context}\n\n선택지:"
        )
        raw = await ctx.gemini.generate_text(model, prompt)
        ctx.log_tokens(model, estimate_tokens(context), estimate_tokens(raw))
        try:
            t = raw.strip()
            if t.startswith("```"):
                t = t.split("\n", 1)[-1].rsplit("```", 1)[0]
            choices = [str(c) for c in json.loads(t)][:n]
        except Exception:
            choices = [f"선택 {i + 1}" for i in range(n)]
        return {"choices": choices}
