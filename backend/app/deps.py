"""공통 의존성 — 인증된 현재 유저, 저장소, 역할 가드.

인증: `Authorization: Bearer <token>`.
- 운영(기본): Supabase 사용자 JWT를 **ES256(비대칭, JWKS)** 로 검증.
  현 Supabase 프로젝트는 비대칭 서명(kid 포함, alg=ES256)을 발급한다.
- 과도기: 레거시 **HS256**(공유 시크릿 `SUPABASE_JWT_SECRET`) 토큰도 함께 허용.
- 개발(DEV_AUTH=true, 실 토큰 검증 경로 없을 때만): `dev:<email>:<role>` 허용(fail-closed).
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Request
from jwt import PyJWKClient

from app.config import Settings, get_settings
from app.errors import ApiError, consent_required, forbidden, unauthorized
from app.store import get_store
from app.store.base import Store
from app.store.records import ProfileRecord

logger = logging.getLogger("app.deps")

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
    token_name: str | None = None  # 토큰 클레임의 표시 이름(user_metadata.full_name|name)


def display_name_from(token_name: str | None, email: str) -> str | None:
    """표시 이름 결정 — 토큰 이름 우선, 없으면 이메일 local-part 폴백(둘 다 없으면 None)."""
    if token_name and token_name.strip():
        return token_name.strip()
    if email and "@" in email:
        local = email.split("@", 1)[0].strip()
        if local:
            return local
    return None


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        raise unauthorized("인증 토큰이 필요합니다.")
    return header.split(" ", 1)[1].strip()


def _resolve_identity(token: str, settings: Settings) -> tuple[str, str, str | None]:
    """토큰에서 (user_id, email, display_name claim) 추출. 이름 클레임 없으면 None."""
    if settings.dev_auth_enabled and token.startswith("dev:"):
        parts = token.split(":")
        if len(parts) < 2 or not parts[1]:
            raise unauthorized("개발 토큰 형식이 올바르지 않습니다. (dev:email:role)")
        email = parts[1].strip().lower()
        user_id = str(uuid.uuid5(_DEV_NAMESPACE, email))
        return user_id, email, None

    payload = _verify_supabase_jwt(token, settings)
    user_id = payload.get("sub")
    email = (payload.get("email") or "").lower()
    if not user_id:
        raise unauthorized("토큰에 사용자 정보가 없습니다.")
    return user_id, email, _name_claim(payload)


def _name_claim(payload: dict) -> str | None:
    """Supabase user JWT 의 표시 이름 클레임 — user_metadata.full_name|name, 그다음 top-level name."""
    meta = payload.get("user_metadata")
    if isinstance(meta, dict):
        for key in ("full_name", "name"):
            val = meta.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    top = payload.get("name")
    return top.strip() if isinstance(top, str) and top.strip() else None


def _verify_supabase_jwt(token: str, settings: Settings) -> dict:
    """Supabase 사용자 JWT 검증. 헤더 alg 로 ES256(JWKS)/HS256(레거시) 분기.

    검증 실패는 **항상 401(unauthorized)** 로 매핑한다(fail-closed). 만료·위조 등 PyJWT 오류뿐
    아니라 JWKS HTTP 비정상 응답(json 디코드 실패)·네트워크 등 예기치 못한 예외도 401 로 처리해
    프론트가 로그인으로 리다이렉트하도록 한다(500 금지).
    """
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
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
    except ApiError:
        raise  # 이미 401 등으로 의도된 응답
    except jwt.PyJWTError:
        # 만료(ExpiredSignatureError)·위조·aud/iss 불일치·형식 오류·JWKS 키 없음 등.
        raise unauthorized("토큰이 유효하지 않거나 만료되었습니다.")
    except Exception as exc:  # noqa: BLE001 — JWKS HTTP 비정상/네트워크 등도 401 로 fail-closed
        logger.warning("토큰 검증 중 예기치 못한 오류 → 401 처리: %r", exc)
        raise unauthorized("토큰을 확인할 수 없어요. 다시 로그인해 주세요.")


def get_store_dep() -> Store:
    return get_store()


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    store: Store = Depends(get_store_dep),
) -> CurrentUser:
    token = _bearer_token(request)
    # JWKS 조회가 네트워크를 탈 수 있어 이벤트 루프를 막지 않도록 스레드로 오프로드.
    user_id, email, token_name = await asyncio.to_thread(_resolve_identity, token, settings)

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
                ProfileRecord(
                    id=user_id, email=email, role="admin",
                    display_name=display_name_from(token_name, email),
                )
            )
        else:
            profile = _backfill_display_name(store, profile, token_name, email)
        return CurrentUser(user_id, email, "admin", profile, needs_onboarding=False, token_name=token_name)

    if profile:
        profile = _backfill_display_name(store, profile, token_name, email)
        return CurrentUser(user_id, email, profile.role, profile, needs_onboarding=False, token_name=token_name)

    # 프로필 미존재 = 온보딩 필요. dev_role 이 있으면 유효 역할로 노출(가드용)하되 온보딩은 필요.
    effective_role = dev_role or "student"
    return CurrentUser(user_id, email, effective_role, None, needs_onboarding=True, token_name=token_name)


def _backfill_display_name(
    store: Store, profile: ProfileRecord, token_name: str | None, email: str
) -> ProfileRecord:
    """표시 이름이 비어 있으면 최초 로그인 시 채운다("이미 있으면 유지"). 실패해도 흐름 불변."""
    if profile.display_name:
        return profile
    value = display_name_from(token_name, email)
    if not value:
        return profile
    try:
        return store.update_profile_fields(profile.id, display_name=value)
    except Exception:
        profile.display_name = value
        return profile


def require_role(*roles: str):
    """특정 역할 전용 엔드포인트 가드 — 위반 시 403."""

    async def _guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise forbidden(f"이 작업은 {'/'.join(roles)} 역할만 가능합니다.")
        return user

    return _guard


def require_guardian_consent():
    """학생의 AI 자유텍스트 기능 게이트 — 보호자 미동의 시 403 consent_required.

    교사/관리자는 면제. 추가기능 03 §5(보호자 동의 실효화).
    """

    async def _guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role == "student":
            consented = bool(user.profile and user.profile.guardian_consent)
            if not consented:
                raise consent_required(
                    "보호자 동의가 있어야 사용할 수 있어요.",
                    {"reason": "guardian_consent"},
                )
        return user

    return _guard
