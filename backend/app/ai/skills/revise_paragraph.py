"""revise_paragraph — 협업 문단 한 개를 지시대로 고쳐 쓴다(교체용, 05-기능수정 §04)."""
from __future__ import annotations

from typing import Any

from app.ai import rag, writer
from app.ai.collab_ctx import resolve
from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class ReviseParagraph(Skill):
    name = "revise_paragraph"
    description = "협업 문단 한 개를 학생 지시대로 고쳐 쓴다. 한 문단을 유지하며 결말은 드러내지 않는다."
    input_schema = {
        "type": "object",
        "properties": {
            "book_id": {"type": "string"},
            "chapter_idx": {"type": "integer"},
            "seq": {"type": "integer"},
            "directive": {"type": "string"},
        },
        "required": ["chapter_idx", "seq", "directive"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        book_id = args.get("book_id") or ctx.book_id
        idx = int(args["chapter_idx"])
        seq = int(args["seq"])
        directive: str = args["directive"]
        bible, event, chapter = resolve(ctx.store, book_id, idx)
        paras = ctx.store.list_paragraphs(chapter.id) if chapter else []
        current = next((p.body for p in paras if p.seq == seq), "")
        context = await rag.retrieve_context(
            ctx.store, ctx.gemini, book_id, current or directive, k=5
        )
        text = await writer.revise_paragraph(ctx.gemini, bible, event, current, directive, context)
        ctx.log_tokens(
            ctx.model_for("writer"), estimate_tokens(current + directive), estimate_tokens(text)
        )
        return {"paragraph": text, "seq": seq}
