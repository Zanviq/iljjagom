"""Imagen 4 삽화 생성 — 챕터마다 1장. Bible 인물 카드로 외형 일관성 유지.

P1에서는 유도(guided) 모드의 `illustration` 이벤트 계약을 만족시키는 데 집중한다.
키가 없으면 결정적 placeholder URL 을 반환한다(실제 업로드는 P2에서 Supabase Storage).
"""
from __future__ import annotations

import hashlib

from app.ai.gemini import GeminiClient


async def generate_illustration(
    gemini: GeminiClient, book_id: str, chapter_idx: int, summary: str, characters: list[dict]
) -> tuple[str, str]:
    """(url, alt) 반환."""
    alt = f"{chapter_idx}장 삽화: {summary[:40]}"
    if gemini.mock or not gemini.settings.use_real_ai:
        seed = hashlib.sha256(f"{book_id}:{chapter_idx}".encode()).hexdigest()[:12]
        url = f"https://placehold.co/768x512?text=ch{chapter_idx}-{seed}"
        return url, alt

    # 실 모델 경로(P2에서 Storage 업로드 연결). 현재는 alt 와 placeholder 로 안전 폴백.
    seed = hashlib.sha256(f"{book_id}:{chapter_idx}".encode()).hexdigest()[:12]
    return f"https://placehold.co/768x512?text=ch{chapter_idx}-{seed}", alt
