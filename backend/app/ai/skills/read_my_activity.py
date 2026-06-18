"""read_my_activity — 총괄 AI: 최근 활동(events 요약). 03-총괄AI-사이드바 §3."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


class ReadMyActivity(Skill):
    name = "read_my_activity"
    description = "학생 본인의 최근 활동 기록(events)을 요약한다(유형별 횟수·마지막 활동 시각)."
    input_schema = {
        "type": "object",
        "properties": {"limit": {"type": "integer"}},
        "required": [],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        user_id = ctx.user_id
        if not user_id:
            return {"byType": {}, "total": 0, "error": "user 없음"}
        limit = int(args.get("limit", 100))
        events = ctx.store.list_events(student_id=user_id, limit=limit)
        by_type: dict[str, int] = {}
        for e in events:
            by_type[e.type] = by_type.get(e.type, 0) + 1
        last_at = max((e.created_at for e in events), default=None)
        return {"byType": by_type, "total": len(events), "lastActivityAt": last_at}
