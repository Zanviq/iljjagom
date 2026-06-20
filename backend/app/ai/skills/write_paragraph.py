"""write_paragraph — 자유집필(기·승) 협업: 학생 의도+설정으로 한 문단 생성(05-기능수정 §04)."""
from __future__ import annotations

from typing import Any

from app.ai import rag, writer
from app.ai.collab_ctx import resolve
from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class WriteParagraph(Skill):
    name = "write_paragraph"
    description = "자유집필 협업에서 학생 의도와 이야기 설정(인물·세계·현재 장 목표)으로 이어질 한 문단을 만든다."
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
        prevs = [p.body for p in ctx.store.list_paragraphs(chapter.id)] if chapter else []
        context = await rag.retrieve_context(ctx.store, ctx.gemini, book_id, intent, k=5)
        text = await writer.write_paragraph(ctx.gemini, bible, event, prevs, intent, context)
        ctx.log_tokens(
            ctx.model_for("writer"), estimate_tokens(intent + context), estimate_tokens(text)
        )
        return {"paragraph": text, "chars": len(text)}
