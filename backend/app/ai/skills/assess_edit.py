"""assess_edit — 학생이 직접 고친 문단이 흐름·설정에서 크게 벗어나는지 판정(05-기능수정 §04)."""
from __future__ import annotations

from typing import Any

from app.ai import chat
from app.ai.collab_ctx import resolve
from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class AssessEdit(Skill):
    name = "assess_edit"
    description = "학생이 직접 고쳐 쓴 문단이 앞뒤·설정과 크게 어긋나는지 보고, 필요하면 부드러운 대안을 제안한다."
    input_schema = {
        "type": "object",
        "properties": {
            "book_id": {"type": "string"},
            "chapter_idx": {"type": "integer"},
            "seq": {"type": "integer"},
            "new_body": {"type": "string"},
        },
        "required": ["chapter_idx", "seq", "new_body"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        book_id = args.get("book_id") or ctx.book_id
        idx = int(args["chapter_idx"])
        seq = int(args["seq"])
        new_body: str = args["new_body"]
        bible, event, chapter = resolve(ctx.store, book_id, idx)
        paras = ctx.store.list_paragraphs(chapter.id) if chapter else []
        prev_body = next((p.body for p in paras if p.seq == seq - 1), "")
        next_body = next((p.body for p in paras if p.seq == seq + 1), "")
        verdict = await chat.assess_edit(
            ctx.gemini, bible, prev_body, next_body, new_body, event.get("objective")
        )
        ctx.log_tokens(ctx.model_for("chat"), estimate_tokens(new_body), 0)
        return verdict
