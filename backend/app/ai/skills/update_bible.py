"""update_bible — Bible(인물·사건·타임라인)에 patch 병합. 외부효과(danger)."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """얕은 깊이 병합 — dict는 재귀, 그 외(list/스칼라)는 patch 로 교체."""
    out = dict(base)
    for key, value in patch.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class UpdateBible(Skill):
    name = "update_bible"
    description = "책의 Bible(JSON)에 인물/사건/세계관 patch 를 병합해 저장한다."
    danger = True
    input_schema = {
        "type": "object",
        "properties": {
            "patch": {"type": "object"},
            "book_id": {"type": "string"},
        },
        "required": ["patch"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        patch: dict[str, Any] = args["patch"]
        book_id = args.get("book_id") or ctx.book_id
        if not book_id:
            return {"ok": False, "error": "book_id 없음"}
        existing = ctx.store.get_bible(book_id)
        merged = _deep_merge(existing.data, patch) if existing else dict(patch)
        ctx.store.upsert_bible(book_id, merged)
        return {"ok": True, "keys": sorted(merged.keys())}
