"""측정 서비스 — 행동 로그(events) 수집 + 학습 결과(learning_artifacts) 저장/조회. 추가기능 04.

원칙: 측정 실패가 학습 흐름을 막지 않는다. 권한 없는 bookId 이벤트는 조용히 누락.
studentId 는 토큰에서만(위조 방지). 학습결과는 신규 테이블 없이 learning_artifacts 재사용.
"""
from __future__ import annotations

from app.ai.safety import check_input
from app.deps import CurrentUser
from app.errors import validation_error
from app.models.schemas import (
    LearningResult,
    LearningResultCreated,
    LearningResultsResponse,
    TrackEvent,
)
from app.services.books import assert_can_access_book, assert_owner_student, get_book_or_404
from app.store.base import Store


def record_events(store: Store, user: CurrentUser, events: list[TrackEvent]) -> int:
    """배치 수집. 권한 검증 통과한 이벤트만 적재하고 적재 수 반환."""
    accepted: list[dict] = []
    for ev in events:
        if ev.book_id:
            book = store.get_book(ev.book_id)
            if not book:
                continue
            try:
                assert_can_access_book(store, user, book)
            except Exception:
                continue
        accepted.append({"book_id": ev.book_id, "type": ev.type, "payload": ev.payload or {}})
    if not accepted:
        return 0
    return store.add_events(user.id, accepted)


def save_learning_result(
    store: Store, user: CurrentUser, book_id: str, type: str, data: dict
) -> LearningResultCreated:
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book) if user.role != "admin" else None

    # emotion 학생 입력 검증(학생/11): 라벨 화이트리스트·value 0~1·장 범위.
    if type == "emotion":
        from app.services.learning import _EMOTION_LABELS

        written = {c.idx for c in store.list_chapters(book_id) if c.char_count > 0}
        for pt in (data.get("points") or []):
            pt = pt or {}
            label = pt.get("label")
            value = pt.get("value")
            cidx = pt.get("chapterIdx", pt.get("chapter_idx"))
            if label is not None and label not in _EMOTION_LABELS:
                raise validation_error("감정 라벨이 올바르지 않아요.", {"field": "label"})
            if value is not None:
                try:
                    if not (0.0 <= float(value) <= 1.0):
                        raise ValueError
                except (TypeError, ValueError):
                    raise validation_error("감정 강도는 0~1 사이여야 해요.", {"field": "value"}) from None
            if cidx is not None and written and cidx not in written:
                raise validation_error("그 장은 아직 없어요.", {"field": "chapterIdx"})

    # essay 자유 텍스트는 안전 게이트 통과 필수.
    if type == "essay":
        for blank in (data.get("blanks") or []):
            text = (blank or {}).get("text") or ""
            safety = check_input(text)
            if not safety.ok:
                store.add_safety_flag(
                    book_id, user.id, "essay", safety.reason or "부적절 표현",
                    category=safety.category,
                )
                raise validation_error(
                    safety.reason or "부적절한 표현이 있어요.",
                    {"suggestion": safety.suggestion},
                )

    rec = store.add_learning_artifact(book_id, type, data)
    return LearningResultCreated(id=rec.id, type=rec.type, created_at=rec.created_at)


def list_learning_results(store: Store, user: CurrentUser, book_id: str) -> LearningResultsResponse:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)
    rows = store.list_learning_artifacts(book_id=book_id)
    return LearningResultsResponse(
        results=[
            LearningResult(id=r.id, type=r.type, data=r.data, created_at=r.created_at)
            for r in rows
            if r.type != "learning_set"  # 생성 교재 캐시는 학생 자기보고 결과가 아님(학생/13)
        ]
    )
