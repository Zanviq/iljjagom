"""retrieve_context — RAG: Bible/청크에서 관련 정보 인출. 03-추가기능/02 카탈로그."""
from __future__ import annotations

from typing import Any

from app.ai import rag
from app.ai.skills.base import Skill, SkillContext, estimate_tokens


class RetrieveContext(Skill):
    name = "retrieve_context"
    description = "질의와 관련된 설정/이전 내용 청크를 벡터 검색으로 인출해 컨텍스트 문자열을 만든다."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "k": {"type": "integer"},
            "book_id": {"type": "string"},
        },
        "required": ["query"],
    }

    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        query: str = args["query"]
        k: int = int(args.get("k", 5))
        book_id = args.get("book_id") or ctx.book_id
        if not book_id:
            return {"context": "", "k": k, "error": "book_id 없음"}
        context = await rag.retrieve_context(ctx.store, ctx.gemini, book_id, query, k=k)
        # 임베딩 호출 1회(질의) — 토큰 추정 기록.
        ctx.log_tokens(ctx.model_for("embed"), estimate_tokens(query), 0)
        return {"context": context, "k": k, "chars": len(context)}
