"""공통 의존성 — 인증된 현재 유저, 저장소, 역할 가드.

인증: `Authorization: Bearer <token>`.
- 운영: Supabase JWT(HS256, SUPABASE_JWT_SECRET) 검증.
- 개발(DEV_AUTH=true): `dev:<email>:<role>` 형식 허용(키 없이 계약 검증용).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.errors import forbidden, unauthorized
from app.store import get_store
from app.store.base import Store
from app.store.records import ProfileRecord

_DEV_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-00000000d39e")


@dataclass
class CurrentUser:
    id: str
    email: str
    role: str  # 유효 역할(admin 화이트리스트 또는 profile.role, 미온보딩이면 'student')
    profile: ProfileRecord | None
    needs_onboarding: bool


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        raise unauthorized("인증 토큰이 필요합니다.")
    return header.split(" ", 1)[1].strip()


def _resolve_identity(token: str, settings: Settings) -> tuple[str, str]:
    """토큰에서 (user_id, email) 추출."""
    if settings.dev_auth and token.startswith("dev:"):
        parts = token.split(":")
        if len(parts) < 2 or not parts[1]:
            raise unauthorized("개발 토큰 형식이 올바르지 않습니다. (dev:email:role)")
        email = parts[1].strip().lower()
        user_id = str(uuid.uuid5(_DEV_NAMESPACE, email))
        return user_id, email

    if not settings.supabase_jwt_secret:
        raise unauthorized("서버에 JWT 검증 설정이 없습니다.")
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError:
        raise unauthorized("토큰이 유효하지 않거나 만료되었습니다.")
    user_id = payload.get("sub")
    email = (payload.get("email") or "").lower()
    if not user_id:
        raise unauthorized("토큰에 사용자 정보가 없습니다.")
    return user_id, email


def get_store_dep() -> Store:
    return get_store()


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    store: Store = Depends(get_store_dep),
) -> CurrentUser:
    token = _bearer_token(request)
    user_id, email = _resolve_identity(token, settings)

    # 개발 토큰의 명시 역할(dev:email:role)
    dev_role = None
    if settings.dev_auth and token.startswith("dev:"):
        parts = token.split(":")
        if len(parts) >= 3 and parts[2]:
            dev_role = parts[2].strip().lower()

    profile = store.get_profile(user_id)

    # 관리자 화이트리스트 → 자동 admin 프로필 보장
    if email in settings.admin_email_set:
        if not profile or profile.role != "admin":
            profile = store.upsert_profile(
                ProfileRecord(id=user_id, email=email, role="admin")
            )
        return CurrentUser(user_id, email, "admin", profile, needs_onboarding=False)

    if profile:
        return CurrentUser(user_id, email, profile.role, profile, needs_onboarding=False)

    # 프로필 미존재 = 온보딩 필요. dev_role 이 있으면 유효 역할로 노출(가드용)하되 온보딩은 필요.
    effective_role = dev_role or "student"
    return CurrentUser(user_id, email, effective_role, None, needs_onboarding=True)


def require_role(*roles: str):
    """특정 역할 전용 엔드포인트 가드 — 위반 시 403."""

    async def _guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise forbidden(f"이 작업은 {'/'.join(roles)} 역할만 가능합니다.")
        return user

    return _guard
