"""persona_reply — 인물 편지 답장(결말 비공개). 03-추가기능/02 카탈로그."""
from __future__ import annotations

from typing import Any

from app.ai import chat
from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class PersonaReply(Skill):
    name = "persona_reply"
    description = "동화 인물의 말투로 학생 편지에 다정하게 답장한다. 결말/줄거리는 누설하지 않는다."
    input_schema = {
        "type": "object",
        "properties": {
            "character_name": {"type": "string"},
            "traits": {"type": "array"},
            "letter_body": {"type": "string"},
        },
        "required": ["character_name", "letter_body"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        reply = await chat.persona_reply(
            ctx.gemini, args["character_name"], args.get("traits", []), args["letter_body"]
        )
        ctx.log_tokens(ctx.model_for("chat"), estimate_tokens(args["letter_body"]), estimate_tokens(reply))
        return {"reply": reply}
