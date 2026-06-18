"""read_progress — 총괄 AI: 책별 진행률/완독 요약. 03-총괄AI-사이드바 §3."""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


class ReadProgress(Skill):
    name = "read_progress"
    description = "특정 책(bookId)의 진행률/완독 상태를 읽는다. bookId 없으면 내 모든 책 요약."
    input_schema = {
        "type": "object",
        "properties": {"book_id": {"type": "string"}},
        "required": [],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        user_id = ctx.user_id
        book_id = args.get("book_id") or ctx.book_id
        if book_id:
            book = ctx.store.get_book(book_id)
            # 본인 책만.
            if not book or (user_id and book.student_id != user_id):
                return {"error": "책을 찾을 수 없거나 접근 불가", "bookId": book_id}
            return {"progress": _book_progress(ctx, book)}
        if not user_id:
            return {"books": [], "error": "user 없음"}
        items = [_book_progress(ctx, b) for b in ctx.store.list_books_for_student(user_id)]
        finished = sum(1 for i in items if i["status"] == "done")
        return {"books": items, "count": len(items), "finished": finished}


def _book_progress(ctx: SkillContext, book) -> dict[str, Any]:
    done = sum(1 for c in ctx.store.list_chapters(book.id) if c.char_count > 0)
    total = book.total_chapters_planned
    return {
        "bookId": book.id,
        "title": book.title,
        "status": book.status,
        "chaptersDone": done,
        "totalChaptersPlanned": total,
        "complete": book.status == "done" or (total is not None and done >= total and total > 0),
    }
