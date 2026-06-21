"""안전 검토 서비스 — 교사/관리자의 안전 신호·보류 편지 검토 루프. 추가기능 03 §4.

상태 머신:
- safety_flags: open → (reviewed) → resolved
- letters(held): held → approved | rejected  (승인/반려 시 연결된 flag 자동 resolved)
"""
from __future__ import annotations

from app.ai import chat
from app.ai.gemini import GeminiClient
from app.deps import CurrentUser
from app.errors import conflict, forbidden, not_found
from app.models.schemas import (
    Letter,
    LettersResponse,
    SafetyFlag,
    SafetyFlagDetail,
    SafetyFlagsResponse,
)
from app.store.base import Store
from app.store.records import LetterRecord, SafetyFlagRecord
from app.util import now_iso


def _assert_class_access(store: Store, user: CurrentUser, class_id: str) -> None:
    if user.role == "admin":
        return
    classroom = store.get_classroom(class_id)
    if not classroom:
        raise not_found("학급을 찾을 수 없습니다.")
    if classroom.teacher_id != user.id:
        raise forbidden("담당 학급만 검토할 수 있습니다.")


def _assert_book_review_access(store: Store, user: CurrentUser, book_id: str | None) -> None:
    """검토(교사/admin) 권한 — 담당 교사 또는 admin. (학생 본인은 검토 불가)"""
    if user.role == "admin":
        return
    if not book_id:
        raise forbidden("권한이 없습니다.")
    book = store.get_book(book_id)
    if not book:
        raise not_found("책을 찾을 수 없습니다.")
    if book.classroom_id:
        classroom = store.get_classroom(book.classroom_id)
        if classroom and classroom.teacher_id == user.id:
            return
    raise forbidden("담당 학급의 항목만 검토할 수 있습니다.")


def _flag_view(f: SafetyFlagRecord) -> SafetyFlag:
    return SafetyFlag(
        id=f.id, book_id=f.book_id, student_id=f.student_id, source=f.source, reason=f.reason,
        category=f.category, severity=f.severity, status=f.status, letter_id=f.letter_id,
        reviewed_by=f.reviewed_by, reviewed_at=f.reviewed_at, note=f.note, created_at=f.created_at,
    )


def _letter_view(m: LetterRecord) -> Letter:
    return Letter(
        id=m.id, book_id=m.book_id, student_id=m.student_id, recipient=m.recipient, body=m.body,
        status=m.status, reply=m.reply, reply_source=m.reply_source,
        reviewed_by=m.reviewed_by, reviewed_at=m.reviewed_at, created_at=m.created_at,
    )


# --- safety_flags ---
def list_class_flags(
    store: Store, user: CurrentUser, class_id: str, status: str | None, source: str | None
) -> SafetyFlagsResponse:
    _assert_class_access(store, user, class_id)
    flags = store.list_safety_flags(class_id=class_id, status=status, source=source)
    return SafetyFlagsResponse(flags=[_flag_view(f) for f in flags])


def list_admin_flags(store: Store, status: str | None) -> SafetyFlagsResponse:
    flags = store.list_safety_flags(status=status)
    return SafetyFlagsResponse(flags=[_flag_view(f) for f in flags])


def get_flag_detail(store: Store, user: CurrentUser, flag_id: str) -> SafetyFlagDetail:
    flag = store.get_safety_flag(flag_id)
    if not flag:
        raise not_found("안전 신호를 찾을 수 없습니다.")
    _assert_book_review_access(store, user, flag.book_id)
    letter = store.get_letter(flag.letter_id) if flag.letter_id else None
    return SafetyFlagDetail(
        **_flag_view(flag).model_dump(),
        letter=_letter_view(letter) if letter else None,
    )


def resolve_flag(
    store: Store, user: CurrentUser, flag_id: str, note: str | None
) -> SafetyFlag:
    flag = store.get_safety_flag(flag_id)
    if not flag:
        raise not_found("안전 신호를 찾을 수 없습니다.")
    _assert_book_review_access(store, user, flag.book_id)
    updated = store.update_safety_flag(
        flag_id, status="resolved", reviewed_by=user.id, reviewed_at=now_iso(), note=note
    )
    return _flag_view(updated)


# --- letters ---
def list_class_letters(
    store: Store, user: CurrentUser, class_id: str, status: str | None
) -> LettersResponse:
    _assert_class_access(store, user, class_id)
    letters = store.list_letters(class_id=class_id, status=status)
    return LettersResponse(letters=[_letter_view(m) for m in letters])


def list_book_letters(store: Store, user: CurrentUser, book_id: str) -> LettersResponse:
    """학생/교사/admin 이 책의 편지 상태·답장을 조회(can_access_book)."""
    from app.services.books import assert_can_access_book, get_book_or_404

    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)
    letters = store.list_letters(book_id=book_id)
    return LettersResponse(letters=[_letter_view(m) for m in letters])


def _resolve_linked_flags(store: Store, user: CurrentUser, letter: LetterRecord, note: str | None) -> None:
    # 편지의 book_id 로 범위를 좁혀 조회한다. 인자 없이 전체를 가져오면 limit(기본 100)에
    # 걸려 신호가 누적된 운영 환경에서 연결 flag 가 resolve 되지 않을 수 있다.
    for f in store.list_safety_flags(book_id=letter.book_id):
        if f.letter_id == letter.id and f.status != "resolved":
            store.update_safety_flag(
                f.id, status="resolved", reviewed_by=user.id, reviewed_at=now_iso(), note=note
            )


async def approve_letter(
    store: Store,
    gemini: GeminiClient,
    user: CurrentUser,
    letter_id: str,
    reply: str | None,
    use_ai_reply: bool,
) -> Letter:
    letter = store.get_letter(letter_id)
    if not letter:
        raise not_found("편지를 찾을 수 없습니다.")
    _assert_book_review_access(store, user, letter.book_id)
    if letter.status not in ("held", "pending"):
        raise conflict("검토 대기 중인 편지가 아닙니다.")

    final_reply = (reply or "").strip()
    reply_source = "teacher"
    if not final_reply and use_ai_reply:
        # 교사가 AI 답장을 쓰기로 함 → 페르소나 답장 생성.
        bible_rec = store.get_bible(letter.book_id)
        characters = bible_rec.data.get("characters", []) if bible_rec else []
        character = next((c for c in characters if c.get("name") == letter.recipient), None)
        final_reply = await chat.persona_reply(
            gemini,
            (character or {}).get("name", letter.recipient),
            (character or {}).get("traits", []),
            letter.body,
        )
        reply_source = "ai"
    if not final_reply:
        raise conflict("답장 내용이 필요합니다(reply 또는 useAiReply).")

    updated = store.update_letter(
        letter_id, status="approved", reply=final_reply, reply_source=reply_source,
        reviewed_by=user.id, reviewed_at=now_iso(),
    )
    _resolve_linked_flags(store, user, letter, "편지 승인")
    return _letter_view(updated)


def reject_letter(
    store: Store, user: CurrentUser, letter_id: str, note: str | None
) -> Letter:
    letter = store.get_letter(letter_id)
    if not letter:
        raise not_found("편지를 찾을 수 없습니다.")
    _assert_book_review_access(store, user, letter.book_id)
    if letter.status not in ("held", "pending"):
        raise conflict("검토 대기 중인 편지가 아닙니다.")
    updated = store.update_letter(
        letter_id, status="rejected", reviewed_by=user.id, reviewed_at=now_iso()
    )
    _resolve_linked_flags(store, user, letter, note or "편지 반려")
    return _letter_view(updated)
