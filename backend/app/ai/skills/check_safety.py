"""check_safety — 입력/출력 안전 게이트. 03-추가기능/02·03."""
from __future__ import annotations

from typing import Any

from app.ai import safety
from app.ai.skills.base import Skill, SkillContext


class CheckSafety(Skill):
    name = "check_safety"
    description = "텍스트의 부적절 표현·정서 위험 신호를 점검한다. ok=False면 차단/안내 대상."
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "kind": {"type": "string"},  # input|output
        },
        "required": ["text"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        text: str = args["text"]
        kind: str = args.get("kind", "input")
        result = safety.check_input(text)
        severity = "high" if not result.ok else ("warn" if result.risk else "ok")
        return {
            "ok": result.ok,
            "reason": result.reason,
            "suggestion": result.suggestion,
            "risk": result.risk,
            "category": result.category,
            "severity": severity,
            "kind": kind,
        }
