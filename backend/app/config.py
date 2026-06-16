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

    # 개발 인증
    dev_auth: bool = True

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def use_supabase(self) -> bool:
        """Supabase 자격이 충분하면 실 DB를, 아니면 인메모리 저장소를 쓴다."""
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def use_real_ai(self) -> bool:
        """Google 키가 있으면 실제 Gemini/Imagen 호출, 없으면 mock."""
        return bool(self.google_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
