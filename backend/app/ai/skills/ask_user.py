"""ask_user — 사용자에게 질문칸을 제시하고 흐름을 일시정지한다(클로드식).

ReAct 오케스트레이터가 이 스킬을 특별 처리한다(세션 awaiting_user, run 은 호출되지 않음).
직접 호출 시에도 안전하게 동작하도록 질문 메타를 그대로 반환한다.
재개는 POST /ai/sessions/{id}/answer.
"""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


class AskUser(Skill):
    name = "ask_user"
    description = "사용자에게 질문과 선택지를 제시하고 응답을 기다린다(흐름 일시정지)."
    input_schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "choices": {"type": "array"},
            "allowText": {"type": "boolean"},
        },
        "required": ["question"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        return {
            "awaiting": True,
            "question": args.get("question"),
            "choices": args.get("choices", []),
            "allowText": bool(args.get("allowText", True)),
        }
