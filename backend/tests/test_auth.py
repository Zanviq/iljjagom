"""인증 토큰 검증 단위 테스트 — ES256(JWKS)·HS256(레거시)·dev fail-closed.

JWKS 네트워크 의존을 피하려 ES256 은 자체 EC 키 + `_jwks_client` monkeypatch 로 검증.
"""
from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import deps
from app.config import Settings
from app.errors import ApiError

ISS = "https://proj.supabase.co/auth/v1"


def _claims(**over):
    now = int(time.time())
    base = {
        "sub": "user-123",
        "email": "Kid@Test.com",
        "aud": "authenticated",
        "iss": ISS,
        "iat": now,
        "exp": now + 3600,
    }
    base.update(over)
    return base


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKS:
    def __init__(self, public_key):
        self._pub = public_key

    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey(self._pub)


def test_es256_verify_ok(monkeypatch):
    priv = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(deps, "_jwks_client", lambda url: _FakeJWKS(priv.public_key()))
    settings = Settings(supabase_url="https://proj.supabase.co", supabase_service_role_key="x")

    tok = jwt.encode(_claims(), priv, algorithm="ES256")
    uid, email = deps._resolve_identity(tok, settings)
    assert uid == "user-123"
    assert email == "kid@test.com"  # 소문자화


def test_es256_rejects_bad_issuer_aud_expiry_tamper(monkeypatch):
    priv = ec.generate_private_key(ec.SECP256R1())
    other = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(deps, "_jwks_client", lambda url: _FakeJWKS(priv.public_key()))
    settings = Settings(supabase_url="https://proj.supabase.co", supabase_service_role_key="x")

    for bad in (
        jwt.encode(_claims(iss="https://evil/auth/v1"), priv, algorithm="ES256"),  # 잘못된 iss
        jwt.encode(_claims(aud="anon"), priv, algorithm="ES256"),  # 잘못된 aud
        jwt.encode(_claims(exp=int(time.time()) - 10), priv, algorithm="ES256"),  # 만료
        jwt.encode(_claims(), other, algorithm="ES256"),  # 다른 키 서명(위조)
    ):
        with pytest.raises(ApiError):
            deps._resolve_identity(bad, settings)


def test_jwks_non_jwt_error_maps_to_401(monkeypatch):
    # JWKS HTTP 비정상(예: 비-JSON 응답 → JSONDecodeError) 등 PyJWTError 아닌 예외도 401 로 fail-closed.
    import json as _json

    priv = ec.generate_private_key(ec.SECP256R1())

    class _BoomJWKS:
        def get_signing_key_from_jwt(self, token):
            raise _json.JSONDecodeError("Expecting value", "<html>", 0)

    monkeypatch.setattr(deps, "_jwks_client", lambda url: _BoomJWKS())
    settings = Settings(supabase_url="https://proj.supabase.co", supabase_service_role_key="x")
    tok = jwt.encode(_claims(), priv, algorithm="ES256")
    with pytest.raises(ApiError) as ei:
        deps._resolve_identity(tok, settings)
    assert ei.value.status_code == 401


def test_malformed_token_maps_to_401():
    settings = Settings(supabase_url="https://proj.supabase.co", supabase_service_role_key="x")
    with pytest.raises(ApiError) as ei:
        deps._resolve_identity("this.is.not-a-real-jwt", settings)
    assert ei.value.status_code == 401


def test_hs256_legacy_verify(monkeypatch):
    settings = Settings(supabase_jwt_secret="test-secret-at-least-32-bytes-long!!", supabase_url="")
    tok = jwt.encode(_claims(), "test-secret-at-least-32-bytes-long!!", algorithm="HS256")
    uid, email = deps._resolve_identity(tok, settings)
    assert uid == "user-123"

    bad = jwt.encode(_claims(), "another-wrong-secret-32-bytes-xxxxxx", algorithm="HS256")
    with pytest.raises(ApiError):
        deps._resolve_identity(bad, settings)


def test_dev_token_disabled_when_supabase_configured():
    # 실 토큰 검증 경로(url)가 있으면 dev 토큰은 비활성(fail-closed).
    settings = Settings(dev_auth=True, supabase_url="https://proj.supabase.co", supabase_jwt_secret="")
    assert settings.dev_auth_enabled is False
    with pytest.raises(ApiError):
        deps._resolve_identity("dev:kid@test.com:teacher", settings)


def test_dev_token_allowed_only_keyless():
    settings = Settings(dev_auth=True, supabase_url="", supabase_jwt_secret="")
    assert settings.dev_auth_enabled is True
    uid, email = deps._resolve_identity("dev:kid@test.com:student", settings)
    assert email == "kid@test.com"
