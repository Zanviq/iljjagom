"""go_to_page — 총괄 AI: 라우트 이동 액션 생성. 03-총괄AI-사이드바 §3."""
from __future__ import annotations

from typing import Any

from app.ai.routes import is_allowed_route
from app.ai.skills.base import Skill, SkillContext


class GoToPage(Skill):
    name = "go_to_page"
    description = "학생을 허용된 화면으로 이동시키는 navigate 액션을 만든다(/home·/learn 등). 외부 URL 불가."
    danger = True  # 외부효과는 없지만 사용자 흐름을 바꾸는 액션 생성.
    input_schema = {
        "type": "object",
        "properties": {"route": {"type": "string"}, "label": {"type": "string"}, "auto": {"type": "boolean"}},
        "required": ["route"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        route: str = args["route"]
        if not is_allowed_route(route):
            return {"ok": False, "error": "허용되지 않은 경로", "route": route}
        action = {
            "type": "navigate",
            "to": route,
            "label": args.get("label") or "이동하기",
            "auto": bool(args.get("auto", False)),
        }
        return {"ok": True, "action": action}
