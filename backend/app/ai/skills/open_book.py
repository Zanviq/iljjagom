"""open_book — 총괄 AI: 특정 책을 상태에 맞는 화면으로 연다. 03-총괄AI-사이드바 §3."""
from __future__ import annotations

from typing import Any

from app.ai.routes import route_for_book
from app.ai.skills.base import Skill, SkillContext


class OpenBook(Skill):
    name = "open_book"
    description = "학생 본인의 책을 상태에 맞는 화면(기획/독서)으로 여는 navigate 액션을 만든다."
    danger = True
    input_schema = {
        "type": "object",
        "properties": {"book_id": {"type": "string"}, "auto": {"type": "boolean"}},
        "required": ["book_id"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        book_id: str = args["book_id"]
        book = ctx.store.get_book(book_id)
        # 본인 책만 열 수 있다(RLS 등가).
        if not book or (ctx.user_id and book.student_id != ctx.user_id):
            return {"ok": False, "error": "책을 찾을 수 없거나 접근 불가", "bookId": book_id}
        route = route_for_book(book.status, book.id)
        label = f"'{book.title}' 열기" if book.title else "책 열기"
        action = {"type": "navigate", "to": route, "label": label, "auto": bool(args.get("auto", False))}
        return {"ok": True, "action": action, "bookId": book.id, "status": book.status}
