"""계정/온보딩 서비스 — /me, /onboarding (FR-A1~A3)."""
from __future__ import annotations

import secrets
import string

from app.deps import CurrentUser, display_name_from
from app.errors import forbidden, validation_error
from app.models.schemas import Me, OnboardingRequest
from app.store.base import Store
from app.store.records import ProfileRecord

CLASS_CODE_LEN = 8


def build_me(user: CurrentUser, store: Store | None = None) -> Me:
    p = user.profile
    class_id: str | None = None
    class_name: str | None = None
    # 학생만 학급을 가진다. 학생이 자기 학급 발제를 찾는 진입점(03 §4.2).
    if store is not None and user.role == "student":
        classrooms = store.list_classrooms_for_student(user.id)
        if classrooms:
            class_id = classrooms[0].id
            class_name = classrooms[0].name
    return Me(
        id=user.id,
        email=user.email,
        role=user.role,
        name=p.display_name if p else None,
        grade=p.grade if p else None,
        guardian_consent=p.guardian_consent if p else False,
        needs_onboarding=user.needs_onboarding,
        class_id=class_id,
        class_name=class_name,
    )


def _generate_class_code(store: Store) -> str:
    # CSPRNG(secrets) 로 추측 어려운 학급 코드 생성. 코드는 가입 권한 경계이므로 random 금지.
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(CLASS_CODE_LEN))
        if not store.get_classroom_by_code(code):
            return code
    raise validation_error("학급 코드를 생성하지 못했습니다. 다시 시도해 주세요.")


def onboard(store: Store, user: CurrentUser, req: OnboardingRequest) -> Me:
    role = req.role  # student | teacher (admin 은 화이트리스트 전용)

    # 권한 상승 차단: 이미 프로필이 있으면 재온보딩으로 역할을 바꿀 수 없다.
    # (최초 역할 선택은 03-기능명세서 §4 계약. 역할 변경은 관리자/별도 절차로만.)
    existing = user.profile or store.get_profile(user.id)
    if existing and existing.role != role:
        raise forbidden("역할은 변경할 수 없습니다. 관리자에게 문의하세요.")

    if role == "student":
        if not req.class_code:
            raise validation_error("학급 코드를 입력해 주세요.", {"field": "classCode"})
        classroom = store.get_classroom_by_code(req.class_code)
        if not classroom:
            raise validation_error("유효하지 않은 학급 코드입니다.", {"field": "classCode"})

    # 표시 이름: 이미 있으면 유지, 없으면 토큰 이름 → 이메일 local-part.
    keep_name = existing.display_name if existing else None
    display_name = keep_name or display_name_from(user.token_name, user.email)
    profile = store.upsert_profile(
        ProfileRecord(
            id=user.id,
            email=user.email,
            role=role,
            guardian_consent=req.guardian_consent,
            grade=req.grade,
            display_name=display_name,
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
    return build_me(refreshed, store)
