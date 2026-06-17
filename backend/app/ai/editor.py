"""Tier3 편집 AI (Gemini Flash, 비동기 검수) — 챕터 초고 품질 점검.

검수 항목(02-backend §3): 말투 일관성 · 시간선 · 학년 어휘 · 학습목표 도달도.
미달 시 해당 부분을 보강해 본문을 반환하고 review_status 를 갱신한다.
학생에게는 대기로 노출되지 않는다(BackgroundTask).

mock 모드에서는 결정적 휴리스틱으로 동작한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.gemini import GeminiClient


@dataclass
class EditResult:
    body: str
    review_status: str  # 'ok' | 'revising'
    notes: list[str] = field(default_factory=list)


_EDITOR_SYSTEM = (
    "너는 어린이 동화 편집자다. 주어진 한 챕터 본문을 검토한다. "
    "말투 일관성, 시간 흐름의 자연스러움, 초등학생 수준의 어휘, "
    "그리고 이 장의 학습 목표가 자연스럽게 녹아 있는지 점검한다. "
    "문제가 있으면 최소한으로 고쳐 매끄럽게 다듬되, 결말을 새로 만들지 않는다. "
    "고친 전체 본문만 출력한다."
)


async def review_chapter(
    gemini: GeminiClient,
    bible: dict[str, Any],
    event: dict[str, Any],
    body: str,
) -> EditResult:
    objective = (event.get("objective") or "").strip()
    notes: list[str] = []

    if gemini.mock:
        revised = body
        # 학습목표 도달도: 목표 키워드가 본문에 없으면 한 문장 보강.
        if objective and objective not in body:
            revised = (
                body.rstrip()
                + f"\n\n그날 배운 '{objective}'은(는) 오래도록 마음에 남았답니다."
            )
            notes.append(f"objective_reinforced:{objective}")
        # mock 은 보강 후 통과 처리(시간선/말투 위반은 만들지 않는다).
        return EditResult(body=revised, review_status="ok", notes=notes)

    obj_line = f"이 장의 학습 목표: {objective}\n" if objective else ""
    prompt = (
        f"{_EDITOR_SYSTEM}\n\n{obj_line}\n검토할 본문:\n{body}\n\n다듬은 본문:"
    )
    revised = (await gemini.generate_text(gemini.settings.gemini_model_flash, prompt)).strip()
    if not revised:
        # 편집 실패 시 원본 유지(학생 본문을 잃지 않는다).
        return EditResult(body=body, review_status="ok", notes=["editor_empty_fallback"])
    return EditResult(body=revised, review_status="ok", notes=notes)
