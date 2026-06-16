"""교사 서비스 — 학급 목록, 발제 생성/조회 (FR-T1)."""
from __future__ import annotations

from app.deps import CurrentUser
from app.errors import forbidden, not_found
from app.models.schemas import (
    Assessment,
    ClassSummary,
    CreatePromptRequest,
    Prompt,
)
from app.store.base import Store
from app.store.records import PromptRecord


def list_classes(store: Store, user: CurrentUser) -> list[ClassSummary]:
    classrooms = store.list_classrooms_for_teacher(user.id)
    return [
        ClassSummary(
            id=c.id,
            name=c.name,
            school_id=c.school_id,
            student_count=store.count_students(c.id),
            code=c.code,
        )
        for c in classrooms
    ]


def _assert_teacher_owns_class(store: Store, user: CurrentUser, class_id: str) -> None:
    classroom = store.get_classroom(class_id)
    if not classroom:
        raise not_found("학급을 찾을 수 없습니다.")
    if user.role != "admin" and classroom.teacher_id != user.id:
        raise forbidden("자기 학급에만 발제를 만들 수 있습니다.")


def _to_prompt(rec: PromptRecord) -> Prompt:
    return Prompt(
        id=rec.id,
        class_id=rec.classroom_id,
        topic=rec.topic,
        learning_objectives=rec.learning_objectives,
        assessment=Assessment(**rec.assessment) if rec.assessment else Assessment(),
        language=rec.language,
        created_at=rec.created_at,
    )


def create_prompt(
    store: Store, user: CurrentUser, class_id: str, req: CreatePromptRequest
) -> Prompt:
    _assert_teacher_owns_class(store, user, class_id)
    rec = store.create_prompt(
        classroom_id=class_id,
        topic=req.topic,
        learning_objectives=req.learning_objectives,
        assessment=req.assessment.model_dump(),
        language=req.language,
    )
    return _to_prompt(rec)


def list_prompts(store: Store, user: CurrentUser, class_id: str) -> list[Prompt]:
    classroom = store.get_classroom(class_id)
    if not classroom:
        raise not_found("학급을 찾을 수 없습니다.")
    # 학급 멤버(교사/학생) 또는 admin 만 열람.
    is_member = (
        user.role == "admin"
        or classroom.teacher_id == user.id
        or store.is_enrolled(class_id, user.id)
    )
    if not is_member:
        raise forbidden("이 학급의 발제를 볼 수 없습니다.")
    return [_to_prompt(p) for p in store.list_prompts_for_class(class_id)]
