"""read_class_prompts — 총괄 AI: 우리 학급 선생님 발제(주제·학습목표). 03-총괄AI-사이드바 §3."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


class ReadClassPrompts(Skill):
    name = "read_class_prompts"
    description = "학생이 속한 학급의 선생님 발제(주제·학습목표) 목록을 읽는다. 새 책의 출발점."
    input_schema = {"type": "object", "properties": {}, "required": []}

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        user_id = ctx.user_id
        if not user_id:
            return {"prompts": [], "error": "user 없음"}
        prompts = []
        for classroom in ctx.store.list_classrooms_for_student(user_id):
            for p in ctx.store.list_prompts_for_class(classroom.id):
                prompts.append({
                    "promptId": p.id,
                    "classId": classroom.id,
                    "className": classroom.name,
                    "topic": p.topic,
                    "learningObjectives": p.learning_objectives,
                })
        return {"prompts": prompts, "count": len(prompts)}
