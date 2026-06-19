"""설정 해석 체인 — 안전강도(선생님/02, 관리자/02).

해석 순서: 발제(prompts.safety_level) > 학급(class_settings.safetyLevel) > 전역(app_settings.safety_level)
> 코드 기본(standard). 출력 정제(filter_output) 호출부가 책 맥락으로 해석값을 주입한다.
(생성 시점 Gemini 유해범주 임계값은 미성년 보호를 위해 strict 유지 — 별도 변경 시 사용자 확인.)
"""
from __future__ import annotations

from app.store.base import Store

_LEVELS = ("relaxed", "standard", "strict")


def resolve_safety_level(store: Store, book_id: str | None = None) -> str:
    levels: list[str | None] = []
    if book_id:
        book = store.get_book(book_id)
        if book:
            if book.prompt_id:
                p = store.get_prompt(book.prompt_id)
                levels.append(getattr(p, "safety_level", None) if p else None)
            if book.classroom_id:
                cs = store.get_class_settings(book.classroom_id)
                levels.append((cs.value or {}).get("safetyLevel") if cs else None)
    try:
        levels.append(store.get_setting("safety_level"))
    except Exception:
        levels.append(None)
    for lvl in levels:
        if lvl in _LEVELS:
            return lvl
    return "standard"
