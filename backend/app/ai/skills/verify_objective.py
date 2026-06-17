"""verify_objective — 학습목표 본문 도달도 검증. 03-추가기능/02·04."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


class VerifyObjective(Skill):
    name = "verify_objective"
    description = "본문에 학습목표가 자연스럽게 도달했는지 점검해 met/missing 으로 나눈다."
    input_schema = {
        "type": "object",
        "properties": {
            "body": {"type": "string"},
            "objectives": {"type": "array"},
            "objective": {"type": "string"},
        },
        "required": ["body"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        body: str = args["body"] or ""
        objectives: list[str] = list(args.get("objectives") or [])
        single = args.get("objective")
        if single and single not in objectives:
            objectives.append(single)
        met = [o for o in objectives if o and o in body]
        missing = [o for o in objectives if o and o not in body]
        return {"met": met, "missing": missing, "allMet": not missing}
