"""Supabase Storage 래퍼 — 삽화 업로드(서비스 롤).

키가 없으면 NoopStorage 로 폴백(업로드 None → 호출자가 placeholder 사용).
버킷 `illustrations`(public)에 `<book_id>/<chapter_idx>.png` 경로로 올린다.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import Settings, get_settings

ILLUSTRATION_BUCKET = "illustrations"

logger = logging.getLogger("app.storage")


class Storage(ABC):
    @abstractmethod
    def upload_illustration(
        self, path: str, data: bytes, content_type: str = "image/png"
    ) -> str | None:
        """업로드 후 공개 URL 반환. 실패/미지원 시 None."""
        ...


class NoopStorage(Storage):
    def upload_illustration(
        self, path: str, data: bytes, content_type: str = "image/png"
    ) -> str | None:
        return None


class SupabaseStorage(Storage):
    def __init__(self, settings: Settings) -> None:
        from supabase import create_client

        self.client = create_client(
            settings.supabase_url, settings.supabase_service_role_key
        )
        self.bucket = ILLUSTRATION_BUCKET

    def upload_illustration(
        self, path: str, data: bytes, content_type: str = "image/png"
    ) -> str | None:
        try:
            self.client.storage.from_(self.bucket).upload(
                path,
                data,
                {"content-type": content_type, "upsert": "true"},
            )
            return self.client.storage.from_(self.bucket).get_public_url(path)
        except Exception:
            return None


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.use_supabase:
        return SupabaseStorage(settings)
    # 운영에서는 삽화가 사라지지 않도록 Noop 금지(fail-closed).
    if not settings.in_memory_allowed:
        raise RuntimeError(
            "운영(APP_ENV=prod)에서 Supabase Storage 자격이 없습니다. "
            "삽화 저장을 위해 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 를 설정하세요."
        )
    if not settings.is_test:
        logger.warning("Supabase 미설정 — 삽화 업로드 비활성(NoopStorage).")
    return NoopStorage()
