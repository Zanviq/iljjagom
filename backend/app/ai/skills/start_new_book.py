"""start_new_book — 총괄 AI: 발제로 새 책을 서버에서 생성하고 기획 페이지 이동. 03-총괄AI-사이드바 §3.

쓰기(책 생성)는 서버에서 처리하고 프론트에는 이동 위치만 돌려준다(00 §5). 본인 학급 발제만.
"""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


class StartNewBook(Skill):
    name = "start_new_book"
    description = "선생님 발제(promptId)로 새 책을 만들고 기획 페이지로 이동하는 액션을 만든다(본인 학급 발제만)."
    danger = True  # 쓰기(책 생성) 외부효과.
    input_schema = {
        "type": "object",
        "properties": {"prompt_id": {"type": "string"}, "auto": {"type": "boolean"}},
        "required": ["prompt_id"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        prompt_id: str = args["prompt_id"]
        user_id = ctx.user_id
        if not user_id:
            return {"ok": False, "error": "user 없음"}
        prompt = ctx.store.get_prompt(prompt_id)
        if not prompt:
            return {"ok": False, "error": "발제를 찾을 수 없음", "promptId": prompt_id}
        # 본인 학급 발제만 책 생성 가능(서비스 계층 RLS 등가).
        if not ctx.store.is_enrolled(prompt.classroom_id, user_id):
            return {"ok": False, "error": "이 발제가 속한 학급의 학생이 아님", "promptId": prompt_id}
        book = ctx.store.create_book(
            student_id=user_id, classroom_id=prompt.classroom_id, prompt_id=prompt_id
        )
        action = {
            "type": "navigate",
            "to": f"/books/{book.id}/plan",
            "label": "책 만들러 가기",
            "auto": bool(args.get("auto", False)),
        }
        return {"ok": True, "action": action, "bookId": book.id, "topic": prompt.topic}
