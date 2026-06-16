"""RAG — 임베딩 + pgvector 인출. 03-기능명세서/02-backend §5.

인출 범위(P1): 현재 챕터 사건 + 등장 인물 카드 + 직전 챕터 요약을
Bible/본문 청크에서 코사인 ANN 으로 가져온다.
"""
from __future__ import annotations

from app.ai.gemini import GeminiClient
from app.store.base import Store


async def index_text(
    store: Store, gemini: GeminiClient, book_id: str, chapter_id: str | None, content: str
) -> None:
    """텍스트 청크를 임베딩해 chapter_chunks 에 적재."""
    for chunk in _split(content):
        embedding = await gemini.embed(chunk)
        store.add_chunk(book_id, chapter_id, chunk, embedding)


async def retrieve_context(
    store: Store, gemini: GeminiClient, book_id: str, query: str, k: int = 5
) -> str:
    """질의와 관련된 청크를 인출해 컨텍스트 문자열로 합친다."""
    query_embedding = await gemini.embed(query)
    chunks = store.search_chunks(book_id, query_embedding, k=k)
    return "\n".join(c.content for c in chunks)


def _split(text: str, max_len: int = 400) -> list[str]:
    """문단/길이 기준 단순 청크 분할."""
    parts: list[str] = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        while len(para) > max_len:
            parts.append(para[:max_len])
            para = para[max_len:]
        if para:
            parts.append(para)
    return parts
