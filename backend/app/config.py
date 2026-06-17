"""환경설정 — Pydantic Settings.

외부 키(Supabase/Google)가 비어 있으면 각각 인메모리 저장소·mock AI로 폴백한다.
이를 통해 키 없이도 03-기능명세서의 계약을 그대로 실행/검증할 수 있다.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Google AI
    google_api_key: str = ""
    gemini_model_pro: str = "gemini-2.5-pro"
    gemini_model_flash: str = "gemini-2.5-flash"
    gemini_model_flash_lite: str = "gemini-2.5-flash-lite"
    gemini_embed_model: str = "gemini-embedding-001"
    imagen_model: str = "imagen-4.0-generate-001"

    # 운영
    admin_emails: str = ""
    allowed_origins: str = "http://localhost:3000"

    # 실행 모드 — dev | test | prod (env APP_ENV).
    # prod 에서 Supabase 자격이 없으면 기동 거부(fail-closed). test/dev 는 인메모리 폴백 허용.
    app_env: str = "dev"
    # 테스트가 인메모리를 명시적으로 허용할 때만 true (conftest 가 켠다).
    allow_in_memory: bool = False

    # rate limit 확장(선택) — 비우면 Store(DB) 기반 폴백.
    redis_url: str = ""

    # 개발 인증 — 보안 기본값은 False(opt-in). 운영에서는 절대 true 금지.
    dev_auth: bool = False

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def supabase_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1" if self.supabase_url else ""

    @property
    def supabase_jwks_url(self) -> str:
        return (
            f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
            if self.supabase_url
            else ""
        )

    @property
    def is_prod(self) -> bool:
        return self.app_env.strip().lower() == "prod"

    @property
    def is_test(self) -> bool:
        return self.app_env.strip().lower() == "test"

    @property
    def use_supabase(self) -> bool:
        """Supabase 자격이 충분하면 실 DB를, 아니면 인메모리 저장소를 쓴다."""
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def in_memory_allowed(self) -> bool:
        """인메모리 폴백 허용 여부. test/ALLOW_IN_MEMORY 면 허용, prod 면 금지.

        운영(prod)에서 Supabase 자격이 없으면 get_store()/main 기동이 거부된다(fail-closed).
        dev 는 개발 편의로 한시 허용(경고 로그).
        """
        return self.is_test or self.allow_in_memory or not self.is_prod

    @property
    def use_real_ai(self) -> bool:
        """Google 키가 있으면 실제 Gemini/Imagen 호출, 없으면 mock."""
        return bool(self.google_api_key)

    @property
    def dev_auth_enabled(self) -> bool:
        """개발 토큰(dev:*)은 명시적 opt-in(dev_auth)이고 실제 JWT 시크릿이 없을 때만 허용.

        운영(시크릿 또는 Supabase URL 존재)에서는 DEV_AUTH 가 실수로 켜져도 우회 경로가 닫힌다(fail-closed).
        실 토큰 검증 경로(HS256 시크릿 또는 ES256 JWKS=supabase_url)가 하나라도 있으면 dev 토큰 비활성.
        """
        return self.dev_auth and not self.supabase_jwt_secret and not self.supabase_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
