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


_COACHING_LEVELS = ("off", "light", "standard")


def resolve_coaching_level(store: Store, book_id: str | None = None) -> str:
    """자유집필 AI 지도 강도 해석(06 §5): 학급(class_settings.coachingLevel) > 기본(light).

    off=점검 생략, light=흐름만(주제 일탈 허용), standard=흐름+주제. 기본은 간섭 완화 위해 light.
    """
    if book_id:
        book = store.get_book(book_id)
        if book and book.classroom_id:
            cs = store.get_class_settings(book.classroom_id)
            lvl = (cs.value or {}).get("coachingLevel") if cs else None
            if lvl in _COACHING_LEVELS:
                return lvl
    return "light"


def resolve_grade(store: Store, book_id: str | None = None, book=None) -> int | None:
    """학년 수준 해석(퀴즈 난이도 맞춤): 발제 권장학년(grade_band) > 학생 프로필 학년 > None.

    book 레코드를 넘기면 재조회를 생략한다. 없으면 None(생성측이 기본 난이도 사용).
    """
    rec = book
    if rec is None and book_id:
        rec = store.get_book(book_id)
    if not rec:
        return None
    if getattr(rec, "prompt_id", None):
        p = store.get_prompt(rec.prompt_id)
        gb = getattr(p, "grade_band", None) if p else None
        if isinstance(gb, int) and gb > 0:
            return gb
    sid = getattr(rec, "student_id", None)
    prof = store.get_profile(sid) if sid else None
    g = getattr(prof, "grade", None) if prof else None
    if isinstance(g, int) and g > 0:
        return g
    return None
