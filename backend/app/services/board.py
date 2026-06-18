"""학급 게시판 서비스 — 완성 책 발표/소개·교사 승인(학생/15 §4 · 14).

편지 승인(safety) 패턴과 형제 구조. 공개 정책은 학급 토글(board_auto_publish, 기본 false=승인 후).
"""
from __future__ import annotations

from app.ai.safety import check_input
from app.deps import CurrentUser
from app.errors import conflict, forbidden, not_found, validation_error
from app.models.schemas import (
    BoardPost,
    BoardPostCreated,
    BoardPostsResponse,
    BoardPostSummary,
)
from app.services.books import assert_owner_student, get_book_or_404
from app.store.base import Store
from app.store.records import ClassPostRecord
from app.util import now_iso


def _is_class_teacher(store: Store, user: CurrentUser, classroom_id: str) -> bool:
    if user.role == "admin":
        return True
    c = store.get_classroom(classroom_id)
    return bool(c and c.teacher_id == user.id)


def _assert_class_member(store: Store, user: CurrentUser, classroom_id: str) -> None:
    if _is_class_teacher(store, user, classroom_id):
        return
    if store.is_enrolled(classroom_id, user.id):
        return
    raise forbidden("이 학급 게시판에 접근할 수 없습니다.")


def _student_name(store: Store, student_id: str) -> str | None:
    prof = store.get_profile(student_id)
    if not prof:
        return None
    if prof.display_name:
        return prof.display_name
    if prof.email and "@" in prof.email:
        return prof.email.split("@", 1)[0]
    return None


def _build_snapshot(store: Store, book) -> dict:
    """발표 스냅샷 — 본문 전체가 아닌 요약/대표 이미지(게시판 목록 가볍게)."""
    chapters = [c for c in store.list_chapters(book.id) if c.char_count > 0]
    cover = next((c.illustration_path for c in chapters if c.illustration_path), None)
    arts = store.list_learning_artifacts(book_id=book.id)
    emotion_logged = any(a.type == "emotion" for a in arts)
    letter_count = sum(1 for a in arts if a.type == "letter")
    quiz = next((a for a in arts if a.type == "quiz"), None)
    snap: dict = {
        "title": book.title,
        "chapterCount": len(chapters),
        "coverIllustration": cover,
        "emotionLogged": emotion_logged,
        "letterCount": letter_count,
    }
    if quiz and isinstance(quiz.data, dict) and "score" in quiz.data:
        snap["quizScore"] = quiz.data.get("score")
    return snap


def create_board_post(
    store: Store, user: CurrentUser, book_id: str, intro: str | None
) -> BoardPostCreated:
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book)
    if book.status != "done":
        raise conflict("완성한 이야기만 학급에 발표할 수 있어요.")
    if not book.classroom_id:
        raise conflict("학급에 속한 책만 발표할 수 있어요.")
    if not store.is_enrolled(book.classroom_id, user.id):
        raise forbidden("이 학급의 학생이 아닙니다.")

    if intro:
        safe = check_input(intro)
        if not safe.ok:
            raise validation_error(safe.reason or "부적절한 표현이 있어요.",
                                   {"suggestion": safe.suggestion})

    classroom = store.get_classroom(book.classroom_id)
    status = "published" if (classroom and classroom.board_auto_publish) else "pending"
    snapshot = _build_snapshot(store, book)
    title = book.title or "제목 없는 이야기"

    existing = store.get_class_post_by_book(book_id)
    if existing:  # 재제출(반려 후 등) → 갱신 + 검토상태 초기화.
        store.update_class_post(
            existing.id, title=title, intro=intro, snapshot=snapshot, status=status,
            reviewed_by=None, reviewed_at=None, review_note=None,
        )
        return BoardPostCreated(post_id=existing.id, status=status)

    rec = store.add_class_post(
        book.classroom_id, book_id, user.id, title, intro, snapshot, status
    )
    return BoardPostCreated(post_id=rec.id, status=status)


def _summary(store: Store, p: ClassPostRecord) -> BoardPostSummary:
    return BoardPostSummary(
        id=p.id, title=p.title, student_name=_student_name(store, p.student_id),
        status=p.status, created_at=p.created_at, snapshot=p.snapshot,
    )


def list_board_posts(
    store: Store, user: CurrentUser, classroom_id: str, status: str | None
) -> BoardPostsResponse:
    _assert_class_member(store, user, classroom_id)
    is_teacher = _is_class_teacher(store, user, classroom_id)
    posts = store.list_class_posts(classroom_id)
    if is_teacher:
        if status:
            posts = [p for p in posts if p.status == status]
    else:
        # 학생은 공개분 + 본인 글(검토 대기/반려 포함).
        posts = [p for p in posts if p.status == "published" or p.student_id == user.id]
    return BoardPostsResponse(posts=[_summary(store, p) for p in posts])


def _to_view(p: ClassPostRecord) -> BoardPost:
    return BoardPost(
        id=p.id, classroom_id=p.classroom_id, book_id=p.book_id, student_id=p.student_id,
        title=p.title, intro=p.intro, snapshot=p.snapshot, status=p.status,
        reviewed_by=p.reviewed_by, reviewed_at=p.reviewed_at, review_note=p.review_note,
        created_at=p.created_at,
    )


def get_board_post(store: Store, user: CurrentUser, post_id: str) -> BoardPost:
    p = store.get_class_post(post_id)
    if not p:
        raise not_found("발표글을 찾을 수 없습니다.")
    if (
        user.role == "admin"
        or p.student_id == user.id
        or _is_class_teacher(store, user, p.classroom_id)
    ):
        return _to_view(p)
    # 그 외 학생: 공개분 + 같은 학급만.
    if p.status == "published" and store.is_enrolled(p.classroom_id, user.id):
        return _to_view(p)
    raise forbidden("이 발표글을 볼 수 없습니다.")


def _review(store: Store, user: CurrentUser, post_id: str, status: str, note: str | None) -> BoardPost:
    p = store.get_class_post(post_id)
    if not p:
        raise not_found("발표글을 찾을 수 없습니다.")
    if not _is_class_teacher(store, user, p.classroom_id):
        raise forbidden("담당 교사만 검토할 수 있습니다.")
    updated = store.update_class_post(
        post_id, status=status, reviewed_by=user.id, reviewed_at=now_iso(), review_note=note,
    )
    return _to_view(updated)


def approve_board_post(store: Store, user: CurrentUser, post_id: str) -> BoardPost:
    return _review(store, user, post_id, "published", None)


def reject_board_post(store: Store, user: CurrentUser, post_id: str, note: str | None) -> BoardPost:
    return _review(store, user, post_id, "rejected", note)
