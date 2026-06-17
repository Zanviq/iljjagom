"""공통 의존성 — 인증된 현재 유저, 저장소, 역할 가드.

인증: `Authorization: Bearer <token>`.
- 운영(기본): Supabase 사용자 JWT를 **ES256(비대칭, JWKS)** 로 검증.
  현 Supabase 프로젝트는 비대칭 서명(kid 포함, alg=ES256)을 발급한다.
- 과도기: 레거시 **HS256**(공유 시크릿 `SUPABASE_JWT_SECRET`) 토큰도 함께 허용.
- 개발(DEV_AUTH=true, 실 토큰 검증 경로 없을 때만): `dev:<email>:<role>` 허용(fail-closed).
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Request
from jwt import PyJWKClient

from app.config import Settings, get_settings
from app.errors import forbidden, unauthorized
from app.store import get_store
from app.store.base import Store
from app.store.records import ProfileRecord

_DEV_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-00000000d39e")
_SUPABASE_AUD = "authenticated"
_ASYM_ALGS = ("ES256", "RS256", "EdDSA")

# JWKS 클라이언트(키 캐시) — URL 당 1개. JWKS 는 거의 변하지 않아 캐시 효율적.
_jwks_clients: dict[str, PyJWKClient] = {}


def _jwks_client(jwks_url: str) -> PyJWKClient:
    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = PyJWKClient(jwks_url, cache_keys=True)
        _jwks_clients[jwks_url] = client
    return client


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
    if settings.dev_auth_enabled and token.startswith("dev:"):
        parts = token.split(":")
        if len(parts) < 2 or not parts[1]:
            raise unauthorized("개발 토큰 형식이 올바르지 않습니다. (dev:email:role)")
        email = parts[1].strip().lower()
        user_id = str(uuid.uuid5(_DEV_NAMESPACE, email))
        return user_id, email

    payload = _verify_supabase_jwt(token, settings)
    user_id = payload.get("sub")
    email = (payload.get("email") or "").lower()
    if not user_id:
        raise unauthorized("토큰에 사용자 정보가 없습니다.")
    return user_id, email


def _verify_supabase_jwt(token: str, settings: Settings) -> dict:
    """Supabase 사용자 JWT 검증. 헤더 alg 로 ES256(JWKS)/HS256(레거시) 분기."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise unauthorized("토큰 형식이 올바르지 않습니다.")
    alg = header.get("alg")

    try:
        if alg in _ASYM_ALGS:
            if not settings.supabase_jwks_url:
                raise unauthorized("서버에 JWKS 설정이 없습니다.")
            signing_key = _jwks_client(settings.supabase_jwks_url).get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=list(_ASYM_ALGS),
                audience=_SUPABASE_AUD,
                issuer=settings.supabase_issuer or None,
                options={"verify_aud": True, "verify_iss": bool(settings.supabase_issuer)},
            )
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise unauthorized("서버에 HS256 시크릿 설정이 없습니다.")
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=_SUPABASE_AUD,
                options={"verify_aud": True},
            )
        raise unauthorized("지원하지 않는 토큰 서명 방식입니다.")
    except jwt.PyJWTError:
        raise unauthorized("토큰이 유효하지 않거나 만료되었습니다.")


def get_store_dep() -> Store:
    return get_store()


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    store: Store = Depends(get_store_dep),
) -> CurrentUser:
    token = _bearer_token(request)
    # JWKS 조회가 네트워크를 탈 수 있어 이벤트 루프를 막지 않도록 스레드로 오프로드.
    user_id, email = await asyncio.to_thread(_resolve_identity, token, settings)

    # 개발 토큰의 명시 역할(dev:email:role)
    dev_role = None
    if settings.dev_auth_enabled and token.startswith("dev:"):
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
