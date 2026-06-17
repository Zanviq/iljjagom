"""Gemini 클라이언트 래퍼 — 모델 등급별 호출 + mock 폴백.

GOOGLE_API_KEY 가 없으면 모든 호출이 결정적 mock 으로 대체된다.
이를 통해 키 없이도 SSE/설계/대화 계약을 그대로 실행할 수 있다.
"""
from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator

from app.config import Settings, get_settings

EMBED_DIM = 768


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

        return await asyncio.to_thread(_call)

    async def stream_text(self, model: str, prompt: str) -> AsyncIterator[str]:
        """토큰(조각) 단위 비동기 스트림. mock 은 호출자가 조립한다(여기선 단일 반환)."""
        if self.mock:
            yield f"[mock:{model}] {prompt[:60]}"
            return

        def _iter():
            return self._client.models.generate_content_stream(model=model, contents=prompt)

        stream = await asyncio.to_thread(_iter)
        for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield text

    async def generate_image(self, prompt: str) -> bytes | None:
        """Imagen 4 로 이미지 1장 생성 → PNG bytes. mock/실패 시 None(호출자가 폴백)."""
        if self.mock:
            return None

        def _call() -> bytes | None:
            try:
                resp = self._client.models.generate_images(
                    model=self.settings.imagen_model, prompt=prompt
                )
                images = getattr(resp, "generated_images", None) or []
                if not images:
                    return None
                image = getattr(images[0], "image", None)
                return getattr(image, "image_bytes", None)
            except Exception:
                return None

        return await asyncio.to_thread(_call)

    async def embed(self, text: str) -> list[float]:
        if self.mock:
            return _deterministic_embedding(text)

        def _call() -> list[float]:
            resp = self._client.models.embed_content(
                model=self.settings.gemini_embed_model, contents=text
            )
            return list(resp.embeddings[0].values)

        return await asyncio.to_thread(_call)


_client: GeminiClient | None = None


def get_gemini() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
