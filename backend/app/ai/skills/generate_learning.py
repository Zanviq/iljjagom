"""generate_learning — 어휘·퀴즈 거리 등 학습 활동 소스 산출. 03-추가기능/02 카탈로그.

전체 LearningResponse 는 서비스(learning.build_learning)가 담당. 본 스킬은 ReAct 관측용으로
책의 학습 소스(어휘 후보·학습목표)를 요약 산출한다.
"""
from __future__ import annotations

from typing import Any

from app.ai.skills.base import Skill, SkillContext


class GenerateLearning(Skill):
    name = "generate_learning"
    description = "책의 어휘 후보·학습목표 등 학습 활동 소스를 요약 산출한다."
    input_schema = {
        "type": "object",
        "properties": {"book_id": {"type": "string"}},
        "required": [],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        book_id = args.get("book_id") or ctx.book_id
        if not book_id:
            return {"error": "book_id 없음"}
        chapters = [c for c in ctx.store.list_chapters(book_id) if c.char_count > 0]
        terms: list[str] = []
        for c in chapters:
            for w in c.words:
                if w not in terms:
                    terms.append(w)
        bible_rec = ctx.store.get_bible(book_id)
        objectives = []
        if bible_rec:
            objectives = [
                e.get("objective") for e in bible_rec.data.get("events", []) if e.get("objective")
            ]
        return {
            "vocabTerms": terms[:8],
            "objectives": objectives,
            "chaptersWritten": len(chapters),
        }
