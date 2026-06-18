"""tutor_answer — 학생의 단어/질문에 친절히 답하는 튜터. 03-추가기능/02 카탈로그."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class TutorAnswer(Skill):
    name = "tutor_answer"
    description = "어린 학생의 단어·질문에 초등학생 눈높이로 쉽게 답한다."
    input_schema = {
        "type": "object",
        "properties": {"question": {"type": "string"}},
        "required": ["question"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        question: str = args["question"]
        if ctx.gemini.mock:
            return {"answer": f"'{question}'에 대해 쉽게 설명해줄게요. 천천히 함께 알아봐요!"}
        model = ctx.model_for("chat")
        prompt = (
            "너는 다정한 초등학교 선생님이다. 학생의 질문에 초등학생 눈높이로 쉽고 짧게(2~3문장) 답한다.\n"
            f"질문: {question}\n\n답:"
        )
        answer = (await ctx.gemini.generate_text(model, prompt)).strip()
        ctx.log_tokens(model, estimate_tokens(question), estimate_tokens(answer))
        return {"answer": answer}
