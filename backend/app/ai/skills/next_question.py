"""next_question — 방금 쓴 문단 뒤 진행 질문 1개(이미 정한 설정은 다시 묻지 않음, §04)."""
from __future__ import annotations

from typing import Any

from app.ai import chat
from app.ai.collab_ctx import resolve
from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class NextQuestion(Skill):
    name = "next_question"
    description = "지금까지 함께 쓴 이야기 뒤에 학생이 상상해 답할 수 있는 진행 질문 한 문장을 만든다."
    input_schema = {
        "type": "object",
        "properties": {
            "book_id": {"type": "string"},
            "chapter_idx": {"type": "integer"},
        },
        "required": ["chapter_idx"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        book_id = args.get("book_id") or ctx.book_id
        idx = int(args["chapter_idx"])
        bible, event, chapter = resolve(ctx.store, book_id, idx)
        paras = [p.body for p in ctx.store.list_paragraphs(chapter.id)] if chapter else []
        question = await chat.next_paragraph_question(ctx.gemini, bible, paras, event)
        ctx.log_tokens(ctx.model_for("chat"), estimate_tokens(" ".join(paras[-3:])), 0)
        return {"question": question}
