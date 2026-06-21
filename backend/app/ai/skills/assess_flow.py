"""assess_flow — 학생 의도가 흐름·주제에 맞는지 판정(generate/coach, 05-기능수정 §04)."""
from __future__ import annotations

from typing import Any

from app.ai import chat
from app.ai.collab_ctx import resolve
from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class AssessFlow(Skill):
    name = "assess_flow"
    description = "학생이 다음에 쓰려는 내용이 직전 문단·이야기 주제와 자연스럽게 이어지는지 판정한다."
    input_schema = {
        "type": "object",
        "properties": {
            "book_id": {"type": "string"},
            "chapter_idx": {"type": "integer"},
            "intent": {"type": "string"},
        },
        "required": ["chapter_idx", "intent"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        book_id = args.get("book_id") or ctx.book_id
        idx = int(args["chapter_idx"])
        intent: str = args["intent"]
        bible, event, chapter = resolve(ctx.store, book_id, idx)
        paras = ctx.store.list_paragraphs(chapter.id) if chapter else []
        prev_body = paras[-1].body if paras else ""
        from app.services.policy import resolve_coaching_level

        level = args.get("coaching_level") or resolve_coaching_level(ctx.store, book_id)
        decision = await chat.assess_flow(
            ctx.gemini, bible, prev_body, event.get("objective"), intent, coaching_level=level
        )
        ctx.log_tokens(ctx.model_for("chat"), estimate_tokens(intent + prev_body), 0)
        return decision
