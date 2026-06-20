"""자유집필 협업 스킬 공용 조회 — (bible, event, chapter) 해석(05-기능수정 §04)."""
from __future__ import annotations

from typing import Any

from app.store.base import Store


def resolve(store: Store, book_id: str | None, idx: int) -> tuple[dict, dict, Any]:
    """책의 Bible·현재 장 event·chapter 레코드를 함께 조회한다.

    secretArc 등은 호출 스킬이 bible_brief 로 걸러 쓰므로 여기서는 원본을 그대로 돌려준다.
    """
    rec = store.get_bible(book_id) if book_id else None
    bible: dict = rec.data if rec else {}
    event: dict = next(
        (e for e in bible.get("events", []) if e.get("chapterIdx") == idx), {}
    ) or {}
    chapter = store.get_chapter(book_id, idx) if book_id else None
    return bible, event, chapter
