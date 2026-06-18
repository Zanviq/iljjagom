"""notify — 알림 생성(관리자/사용자/역할/브로드캐스트). 외부효과(danger). 03-추가기능/02·06."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


class Notify(Skill):
    name = "notify"
    description = "알림을 생성한다(특정 사용자/역할/전체). 운영·관측용."
    danger = True
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
            "level": {"type": "string"},
            "target_user_id": {"type": "string"},
            "target_role": {"type": "string"},
            "is_broadcast": {"type": "boolean"},
        },
        "required": ["title"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        rec = ctx.store.create_notification(
            title=args["title"],
            body=args.get("body"),
            level=args.get("level", "info"),
            target_user_id=args.get("target_user_id"),
            target_role=args.get("target_role"),
            is_broadcast=bool(args.get("is_broadcast", False)),
        )
        return {"id": rec.id, "level": rec.level}
