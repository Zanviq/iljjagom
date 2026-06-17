"""Gemini 클라이언트 래퍼 — 모델 등급별 호출 + mock 폴백.

GOOGLE_API_KEY 가 없으면 모든 호출이 결정적 mock 으로 대체된다.
이를 통해 키 없이도 SSE/설계/대화 계약을 그대로 실행할 수 있다.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import AsyncIterator, Callable
from typing import TypeVar

from app.config import Settings, get_settings

EMBED_DIM = 768

# 일시 오류(과부하/한도) 신호 — 짧은 백오프 후 재시도.
_TRANSIENT_SIGNALS = ("503", "unavailable", "overloaded", "429", "resource_exhausted", "rate")
_T = TypeVar("_T")


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(sig in msg for sig in _TRANSIENT_SIGNALS)


def _retry_call(fn: Callable[[], _T], attempts: int = 3, base_delay: float = 1.0) -> _T:
    """동기 호출을 일시 오류 시 지수 백오프로 재시도(to_thread 내부에서 실행)."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — 일시 오류만 재시도, 그 외 재던짐
            last = e
            if not _is_transient(e) or i == attempts - 1:
                raise
            time.sleep(base_delay * (2 ** i))
    assert last is not None
    raise last


def _deterministic_embedding(text: str, dim: int = EMBED_DIM) -> list[float]:
    """텍스트로부터 결정적 임베딩 생성(mock). 코사인 검색이 동작하도록 정규화 전 단계."""
    vec: list[float] = []
    counter = 0
    while len(vec) < dim:
        h = hashlib.sha256(f"{text}:{counter}".encode("utf-8")).digest()
        for b in h:
            vec.append((b / 255.0) * 2.0 - 1.0)
            if len(vec) >= dim:
                break
        counter += 1
    return vec


class GeminiClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.use_real_ai:
            from google import genai

            self._client = genai.Client(api_key=self.settings.google_api_key)

    @property
    def mock(self) -> bool:
        return self._client is None

    async def generate_text(self, model: str, prompt: str) -> str:
        if self.mock:
            return f"[mock:{model}] {prompt[:60]}"

        def _call() -> str:
            resp = self._client.models.generate_content(model=model, contents=prompt)
            return resp.text or ""

        return await asyncio.to_thread(lambda: _retry_call(_call))

    async def stream_text(self, model: str, prompt: str) -> AsyncIterator[str]:
        """토큰(조각) 단위 비동기 스트림. mock 은 호출자가 조립한다(여기선 단일 반환)."""
        if self.mock:
            yield f"[mock:{model}] {prompt[:60]}"
            return

        def _iter():
            return self._client.models.generate_content_stream(model=model, contents=prompt)

        stream = await asyncio.to_thread(lambda: _retry_call(_iter))
        for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield text

    async def generate_image(self, prompt: str) -> bytes | None:
        """Imagen 4 로 이미지 1장 생성 → PNG bytes. mock/실패 시 None(호출자가 폴백)."""
        if self.mock:
            return None

        def _call() -> bytes | None:
            resp = self._client.models.generate_images(
                model=self.settings.imagen_model, prompt=prompt
            )
            images = getattr(resp, "generated_images", None) or []
            if not images:
                return None
            image = getattr(images[0], "image", None)
            return getattr(image, "image_bytes", None)

        def _safe() -> bytes | None:
            # 일시 오류는 재시도하고, 그 외 실패는 None 으로 폴백(placeholder 사용).
            try:
                return _retry_call(_call)
            except Exception:
                return None

        return await asyncio.to_thread(_safe)

    async def embed(self, text: str) -> list[float]:
        if self.mock:
            return _deterministic_embedding(text)

        def _call() -> list[float]:
            from google.genai import types

            # gemini-embedding-001 기본 출력은 3072차원이라, DB 스키마/HNSW(vector(768))에
            # 맞춰 output_dimensionality 로 768 로 줄인다(코사인 검색이라 별도 정규화 불필요).
            resp = self._client.models.embed_content(
                model=self.settings.gemini_embed_model,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=EMBED_DIM),
            )
            return list(resp.embeddings[0].values)

        return await asyncio.to_thread(lambda: _retry_call(_call))


_client: GeminiClient | None = None


def get_gemini() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
