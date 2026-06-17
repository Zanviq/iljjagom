"""Tier2 집필 AI (Gemini 2.5 Flash, 챕터마다, SSE) — RAG 컨텍스트 고정 본문 생성.

stream_chapter 는 본문 조각(token)을 비동기로 yield 한다.
SSE 오케스트레이션(meta/illustration/prompt/token/done)은 서비스 계층이 담당.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from app.ai.gemini import GeminiClient


def build_prompt(bible: dict[str, Any], event: dict[str, Any], rag_context: str) -> str:
    chars = ", ".join(c.get("name", "") for c in bible.get("characters", []))
    tone = bible.get("world", {}).get("tone", "따뜻한")
    objective = event.get("objective")
    obj_line = f"이 장에서 자연스럽게 담을 학습 내용: {objective}\n" if objective else ""
    return (
        "너는 어린이 동화 작가다. 초등학생이 읽기 쉬운 한국어로 한 챕터를 쓴다. "
        f"분위기는 {tone}. 등장인물: {chars}. "
        "결말을 미리 드러내지 말고 이 장면만 생생히 묘사한다.\n"
        f"{obj_line}"
        f"참고(설정/이전 내용):\n{rag_context}\n\n"
        f"이번 장 개요: {event.get('summary', '')}\n\n본문:"
    )


def _mock_chapter_text(bible: dict[str, Any], event: dict[str, Any]) -> str:
    hero = "주인공"
    chars = bible.get("characters", [])
    if chars:
        hero = chars[0].get("name", "주인공")
    objective = event.get("objective") or "새로운 것"
    idx = event.get("chapterIdx", 1)
    return (
        f"{idx}장.\n"
        f"{hero}은(는) 오늘도 호기심 가득한 눈으로 길을 나섰어요. "
        f"오늘은 '{objective}'에 대해 알아보기로 한 날이거든요.\n"
        f"\"이게 정말 그렇게 되는 걸까?\" {hero}은(는) 고개를 갸웃했어요. "
        f"바람이 살랑 불어오자, 작은 단서 하나가 눈앞에 나타났어요.\n"
        f"{hero}은(는) 한 걸음 더 가까이 다가가 보았어요. "
        f"두근거리는 마음으로, 이야기는 이제 막 시작되고 있었답니다."
    )


def select_words(text: str) -> list[str]:
    """본문에서 단어 도움 대상 후보를 뽑는다(P1 최소: 길이 기준)."""
    seen: list[str] = []
    for raw in text.replace("\n", " ").split(" "):
        token = "".join(ch for ch in raw if ch.isalnum())
        if len(token) >= 3 and token not in seen:
            seen.append(token)
        if len(seen) >= 5:
            break
    return seen


async def stream_chapter(
    gemini: GeminiClient,
    bible: dict[str, Any],
    event: dict[str, Any],
    rag_context: str,
) -> AsyncIterator[str]:
    """본문 토큰 스트림."""
    if gemini.mock:
        text = _mock_chapter_text(bible, event)
        # 글자 단위 흐름을 흉내 내어 작은 조각으로 흘린다.
        for i in range(0, len(text), 4):
            await asyncio.sleep(0)  # 이벤트 루프 양보
            yield text[i : i + 4]
        return

    prompt = build_prompt(bible, event, rag_context)
    async for chunk in gemini.stream_text(gemini.settings.gemini_model_flash, prompt):
        yield chunk


async def revise_text(
    gemini: GeminiClient,
    bible: dict[str, Any],
    event: dict[str, Any],
    rag_context: str,
    current_body: str,
    directive: str,
) -> str:
    """수정 요청(해석된 directive)을 반영해 챕터 전체 본문을 재생성한다(비스트림).

    자유모드 수정요청(FR-S6) 파이프라인의 집필 단계. 결말은 새로 만들지 않는다.
    """
    if gemini.mock:
        hero = "주인공"
        chars = bible.get("characters", [])
        if chars:
            hero = chars[0].get("name", "주인공")
        # 결정적 재생성: 기존 본문 + 수정 directive 를 반영한 단락을 덧붙인다.
        return (
            current_body.rstrip()
            + f"\n\n{hero}은(는) 마음을 고쳐먹었어요. ({directive}) "
            f"그러자 이야기는 한결 또렷해졌답니다."
        )

    prompt = (
        "너는 어린이 동화 작가다. 아래 본문을 독자의 요청에 맞게 자연스럽게 고쳐 쓴다. "
        "결말을 새로 만들지 말고, 이 장면의 흐름은 유지한 채 요청만 반영한다. "
        "고친 전체 본문만 출력한다.\n"
        f"분위기 참고: {bible.get('world', {}).get('tone', '따뜻한')}\n"
        f"설정 참고:\n{rag_context}\n\n"
        f"독자 요청: {directive}\n\n현재 본문:\n{current_body}\n\n고친 본문:"
    )
    return (await gemini.generate_text(gemini.settings.gemini_model_flash, prompt)).strip()
