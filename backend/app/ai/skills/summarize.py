"""summarize — 챕터/사건 요약(다음 챕터 RAG·Bible용). 03-추가기능/02 카탈로그."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class Summarize(Skill):
    name = "summarize"
    description = "긴 텍스트를 짧게 요약한다. 다음 챕터 컨텍스트·Bible 갱신에 쓴다."
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "max_len": {"type": "integer"},
        },
        "required": ["text"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        text: str = args["text"] or ""
        max_len: int = int(args.get("max_len", 200))
        if ctx.gemini.mock:
            # 결정적 요약: 첫 문장 또는 max_len 까지.
            first = text.strip().split("\n", 1)[0]
            summary = first[:max_len]
        else:
            model = ctx.model_for("chat")
            prompt = (
                "다음 글을 어린이 책 맥락 유지를 위해 한국어 2~3문장으로 요약해라. 요약만 출력.\n\n"
                f"{text}"
            )
            summary = (await ctx.gemini.generate_text(model, prompt)).strip()[:max_len]
            ctx.log_tokens(model, estimate_tokens(text), estimate_tokens(summary))
        return {"summary": summary, "chars": len(summary)}
