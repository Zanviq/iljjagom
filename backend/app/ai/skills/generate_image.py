"""generate_image — 삽화(Imagen)+Storage 업로드. 외부효과(danger)."""
from __future__ import annotations

from typing import Any

from app.ai import imagen
from app.ai.skills.base import Skill, SkillContext


class GenerateImage(Skill):
    name = "generate_image"
    description = "장면 요약과 인물 카드로 삽화를 생성해 Storage 에 올리고 URL 을 반환한다. 인물 외형 일관."
    danger = True
    input_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "chapter_idx": {"type": "integer"},
            "characters": {"type": "array"},
            "book_id": {"type": "string"},
        },
        "required": ["summary", "chapter_idx"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        book_id = args.get("book_id") or ctx.book_id
        if not book_id:
            return {"url": None, "error": "book_id 없음"}
        chapter_idx = int(args["chapter_idx"])
        characters = args.get("characters") or []
        url, alt = await imagen.generate_illustration(
            ctx.gemini, book_id, chapter_idx, args["summary"], characters
        )
        # 이미지 호출 비용(추정) 기록.
        ctx.log_tokens(ctx.model_for("imagen"), 0, 0)
        return {"url": url, "alt": alt}
