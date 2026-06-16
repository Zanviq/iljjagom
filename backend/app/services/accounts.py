"""계정/온보딩 서비스 — /me, /onboarding (FR-A1~A3)."""
from __future__ import annotations

import random
import string

from app.deps import CurrentUser
from app.errors import validation_error
from app.models.schemas import Me, OnboardingRequest
from app.store.base import Store
from app.store.records import ProfileRecord


def build_me(user: CurrentUser) -> Me:
    p = user.profile
    return Me(
        id=user.id,
        email=user.email,
        role=user.role,
        grade=p.grade if p else None,
        guardian_consent=p.guardian_consent if p else False,
        needs_onboarding=user.needs_onboarding,
    )


def _generate_class_code(store: Store) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = "".join(random.choices(alphabet, k=6))
        if not store.get_classroom_by_code(code):
            return code
    raise validation_error("학급 코드를 생성하지 못했습니다. 다시 시도해 주세요.")


def onboard(store: Store, user: CurrentUser, req: OnboardingRequest) -> Me:
    role = req.role  # student | teacher (admin 은 화이트리스트 전용)

    if role == "student":
        if not req.class_code:
            raise validation_error("학급 코드를 입력해 주세요.", {"field": "classCode"})
        classroom = store.get_classroom_by_code(req.class_code)
        if not classroom:
            raise validation_error("유효하지 않은 학급 코드입니다.", {"field": "classCode"})

    profile = store.upsert_profile(
        ProfileRecord(
            id=user.id,
            email=user.email,
            role=role,
            guardian_consent=req.guardian_consent,
            grade=req.grade,
        )
    )

    if role == "student":
        classroom = store.get_classroom_by_code(req.class_code)  # type: ignore[arg-type]
        store.enroll(classroom.id, user.id)
    elif role == "teacher":
        # 교사 온보딩 시 기본 학급 자동 생성(학생이 코드로 가입할 수 있도록).
        if not store.list_classrooms_for_teacher(user.id):
            code = _generate_class_code(store)
            store.create_classroom(teacher_id=user.id, name="우리 반", code=code)

    refreshed = CurrentUser(
        id=user.id, email=user.email, role=role, profile=profile, needs_onboarding=False
    )
    return build_me(refreshed)
