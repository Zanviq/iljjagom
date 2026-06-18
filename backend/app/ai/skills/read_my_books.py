"""read_my_books — 총괄 AI: 내(학생)가 만든 책 목록+상태+진행률. 03-총괄AI-사이드바 §3."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


class ReadMyBooks(Skill):
    name = "read_my_books"
    description = "학생 본인이 만든 책 목록과 각 책의 상태·진행률(쓴 장수/계획 장수)을 읽는다."
    input_schema = {"type": "object", "properties": {}, "required": []}

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        user_id = ctx.user_id
        if not user_id:
            return {"books": [], "error": "user 없음"}
        books = []
        for rec in ctx.store.list_books_for_student(user_id):
            done = sum(1 for c in ctx.store.list_chapters(rec.id) if c.char_count > 0)
            books.append({
                "bookId": rec.id,
                "title": rec.title,
                "status": rec.status,
                "chaptersDone": done,
                "totalChaptersPlanned": rec.total_chapters_planned,
                "updatedAt": rec.updated_at or rec.created_at,
            })
        return {"books": books, "count": len(books)}
