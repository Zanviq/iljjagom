"""Imagen 4 삽화 생성 — 챕터마다 1장. Bible 인물 카드로 외형 일관성 유지.

실 모델 경로: Imagen 으로 이미지 생성 → Supabase Storage(illustrations 버킷) 업로드 → 공개 URL.
키가 없거나 실패하면 결정적 placeholder URL 로 안전 폴백한다(계약/SSE 흐름 불변).
"""
from __future__ import annotations

import hashlib

from app.ai.gemini import GeminiClient
from app.storage import get_storage


def _placeholder(book_id: str, chapter_idx: int) -> str:
    seed = hashlib.sha256(f"{book_id}:{chapter_idx}".encode()).hexdigest()[:12]
    return f"https://placehold.co/768x512?text=ch{chapter_idx}-{seed}"


def _build_image_prompt(summary: str, characters: list[dict]) -> str:
    who = "; ".join(
        f"{c.get('name', '')}({c.get('appearance', '')})" for c in characters[:3]
    )
    return (
        "어린이 동화책 삽화, 따뜻하고 부드러운 색감, 안전한 그림체. "
        f"등장인물: {who}. 장면: {summary}"
    )


async def generate_illustration(
    gemini: GeminiClient, book_id: str, chapter_idx: int, summary: str, characters: list[dict]
) -> tuple[str, str]:
    """(url, alt) 반환."""
    alt = f"{chapter_idx}장 삽화: {summary[:40]}"

    if gemini.mock or not gemini.settings.use_real_ai:
        return _placeholder(book_id, chapter_idx), alt

    # 실 모델: Imagen 생성 → Storage 업로드. 어느 단계든 실패하면 placeholder.
    data = await gemini.generate_image(_build_image_prompt(summary, characters))
    if data:
        url = get_storage().upload_illustration(f"{book_id}/{chapter_idx}.png", data)
        if url:
            return url, alt
    return _placeholder(book_id, chapter_idx), alt
