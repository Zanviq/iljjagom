"""Gemini 클라이언트 래퍼 — 모델 등급별 호출 + mock 폴백.

GOOGLE_API_KEY 가 없으면 모든 호출이 결정적 mock 으로 대체된다.
이를 통해 키 없이도 SSE/설계/대화 계약을 그대로 실행할 수 있다.
"""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import logging
import time
from collections.abc import AsyncIterator, Callable
from typing import TypeVar

from app.config import Settings, get_settings
from app.errors import ai_unavailable

logger = logging.getLogger("app.ai.gemini")

EMBED_DIM = 768

# 마지막 LLM 텍스트 프롬프트 스냅샷(태스크 로컬, 관측용). generate_text/stream_text 가 채우고
# SkillContext.emit 이 ai_steps.args._prompt 로 1회 적재 후 소비(비운다). 임베딩은 제외(PII·대용량).
# contextvars 라 요청(=asyncio Task)마다 격리되어 동시성 오염이 없다(관리자/01 §4-B).
last_prompt_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "gemini_last_prompt", default=None
)

# 일시 오류(과부하/한도) 신호 — 짧은 백오프 후 재시도.
_TRANSIENT_SIGNALS = ("503", "unavailable", "overloaded", "429", "resource_exhausted", "rate")
_T = TypeVar("_T")

# 미성년 전제 콘텐츠 안전 — 텍스트 생성에 적용(추가기능 03 §3.3).
_HARM_CATEGORIES = (
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
)
# strict(기본): 낮은 확률부터 차단. normal: 중간 이상 차단.
_THRESHOLDS = {"strict": "BLOCK_LOW_AND_ABOVE", "normal": "BLOCK_MEDIUM_AND_ABOVE"}


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
        # 미성년 전제 — 기본 strict. (관리자 app_settings.safety_level 연동은 후속.)
        self.safety_level = "strict"
        if self.settings.use_real_ai:
            from google import genai

            self._client = genai.Client(api_key=self.settings.google_api_key)

    @property
    def mock(self) -> bool:
        return self._client is None

    def _gen_config(self):
        """텍스트 생성 config — 콘텐츠 안전 설정 포함. 실패 시 None(설정 없이 호출)."""
        try:
            from google.genai import types

            threshold = _THRESHOLDS.get(self.safety_level, _THRESHOLDS["strict"])
            return types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(category=cat, threshold=threshold)
                    for cat in _HARM_CATEGORIES
                ]
            )
        except Exception:
            return None

    async def generate_text(self, model: str, prompt: str) -> str:
        last_prompt_var.set(prompt)  # 관측: 다음 emit 이 ai_steps 에 적재
        if self.mock:
            return f"[mock:{model}] {prompt[:60]}"

        config = self._gen_config()

        def _call() -> str:
            resp = self._client.models.generate_content(
                model=model, contents=prompt, config=config
            )
            return resp.text or ""

        try:
            return await asyncio.to_thread(lambda: _retry_call(_call))
        except Exception as e:  # 제공자 오류 → 깔끔한 503(ai_unavailable). 500 raw 방지(CORS 포함).
            logger.warning("gemini generate_text 실패: %s", e)
            raise ai_unavailable() from e

    async def stream_text(self, model: str, prompt: str) -> AsyncIterator[str]:
        """토큰(조각) 단위 비동기 스트림. mock 은 호출자가 조립한다(여기선 단일 반환)."""
        last_prompt_var.set(prompt)  # 관측: 다음 emit 이 ai_steps 에 적재
        if self.mock:
            yield f"[mock:{model}] {prompt[:60]}"
            return

        config = self._gen_config()

        def _iter():
            return self._client.models.generate_content_stream(
                model=model, contents=prompt, config=config
            )

        try:
            stream = await asyncio.to_thread(lambda: _retry_call(_iter))
            for chunk in stream:
                text = getattr(chunk, "text", None)
                if text:
                    yield text
        except Exception as e:  # 스트림 제공자 오류 → 503(호출부가 폴백/재시도 에러로 처리)
            logger.warning("gemini stream_text 실패: %s", e)
            raise ai_unavailable() from e

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
                logger.warning("imagen: 생성 결과 비어 있음(generated_images empty)")
                return None
            image = getattr(images[0], "image", None)
            data = getattr(image, "image_bytes", None)
            if not data:
                logger.warning("imagen: image_bytes 없음")
            return data

        def _safe() -> bytes | None:
            # 일시 오류는 재시도하고, 그 외 최종 실패는 로그 후 None 폴백(placeholder).
            try:
                return _retry_call(_call)
            except Exception as e:
                logger.warning("imagen 생성 실패: %s", e)
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

        try:
            return await asyncio.to_thread(lambda: _retry_call(_call))
        except Exception as e:  # 임베딩 제공자 오류 → 503
            logger.warning("gemini embed 실패: %s", e)
            raise ai_unavailable() from e


_client: GeminiClient | None = None


def get_gemini() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
