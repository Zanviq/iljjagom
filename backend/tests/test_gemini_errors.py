"""Gemini 제공자 오류 → 깔끔한 503 ai_unavailable 매핑(원시 500·CORS 누락 방지)."""
from __future__ import annotations

import pytest

from app.ai.gemini import GeminiClient
from app.errors import ApiError


class _RaisingModels:
    def generate_content(self, **_k):
        raise RuntimeError("provider down")

    def embed_content(self, **_k):
        raise RuntimeError("provider down")


class _RaisingClient:
    models = _RaisingModels()


async def test_generate_text_maps_provider_error_to_ai_unavailable():
    gc = GeminiClient()
    gc._client = _RaisingClient()  # 비-None → mock=False(실 호출 경로)
    with pytest.raises(ApiError) as ei:
        await gc.generate_text("model", "prompt")
    assert ei.value.code == "ai_unavailable" and ei.value.status_code == 503


async def test_embed_maps_provider_error_to_ai_unavailable():
    gc = GeminiClient()
    gc._client = _RaisingClient()  # 비-None → mock=False(실 호출 경로)
    with pytest.raises(ApiError) as ei:
        await gc.embed("text")
    assert ei.value.code == "ai_unavailable"
