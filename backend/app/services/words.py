"""단어 도움 — FR-S7. 본문 단어의 발음/뜻 (P1 최소: 단순 사전 응답 수준)."""
from __future__ import annotations

from app.ai.gemini import GeminiClient
from app.models.schemas import Word


async def lookup(gemini: GeminiClient, term: str) -> Word:
    term = term.strip()
    if gemini.mock:
        return Word(term=term, reading=term, meaning=f"'{term}'의 뜻 풀이(준비 중)")

    prompt = (
        f"초등학생이 이해할 수 있게 '{term}' 단어의 뜻을 한 문장으로 쉽게 설명해 줘. "
        "설명 문장만 출력해."
    )
    meaning = await gemini.generate_text(gemini.settings.gemini_model_flash_lite, prompt)
    return Word(term=term, reading=term, meaning=meaning.strip() or term)
