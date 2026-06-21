"""Tier1 설계 AI (Gemini 2.5 Pro, 책당 1회) — Bible 생성 + 학습목표 챕터 분배.

출력 Bible(jsonb): 인물 카드 / 세계관 / 사건 시퀀스 / 학습목표→챕터 분배 / 후반 큰줄기(비공개).
후반 큰줄기는 아동에게 직접 노출되지 않으며 집필/유도 단계에서만 참조한다.
"""
from __future__ import annotations

import json
from typing import Any

from app.ai.gemini import GeminiClient
from app.store.records import PromptRecord

DEFAULT_TOTAL_CHAPTERS = 6


def _distribute_objectives(objectives: list[str], total: int) -> list[dict[str, Any]]:
    """학습목표를 챕터에 순환 분배."""
    events = []
    for i in range(total):
        # 앞쪽(기·승)은 자유, 뒤쪽(전·결)은 유도.
        mode = "free" if i < total // 2 else "guided"
        obj = objectives[i % len(objectives)] if objectives else None
        events.append(
            {
                "chapterIdx": i + 1,
                "mode": mode,
                "objective": obj,
                "summary": f"{i + 1}장: 학습목표 '{obj}' 를 사건으로 풀어낸다." if obj else f"{i + 1}장",
            }
        )
    return events


def _normalize_bible(
    data: dict[str, Any], objectives: list[str], default_total: int
) -> dict[str, Any]:
    """LLM Bible 결과를 안전하게 정규화(이슈a 재발 방지).

    실 Gemini 가 events 를 totalChaptersPlanned 만큼 채우지 못하거나 chapterIdx 가
    누락되면, 해당 장의 event/챕터 행이 안 만들어져 독서 시 '해당 챕터가 없습니다' 가 된다.
    여기서 events 를 1..total 로 완전히 채우고 앞 절반 free / 뒤 절반 guided 를 강제한다.
    """
    if not isinstance(data, dict):
        data = {}
    raw_total = data.get("totalChaptersPlanned")
    events_in = data.get("events") if isinstance(data.get("events"), list) else []
    total = raw_total if isinstance(raw_total, int) and raw_total > 0 else (len(events_in) or default_total)
    total = max(2, min(int(total), 12))  # 합리 범위로 제한

    by_idx: dict[int, dict] = {}
    for e in events_in:
        if isinstance(e, dict) and isinstance(e.get("chapterIdx"), int):
            by_idx[e["chapterIdx"]] = e

    norm: list[dict[str, Any]] = []
    for tmpl in _distribute_objectives(objectives, total):
        src = by_idx.get(tmpl["chapterIdx"], {})
        norm.append(
            {
                "chapterIdx": tmpl["chapterIdx"],
                "mode": tmpl["mode"],  # 앞 절반 free / 뒤 절반 guided 강제(게이트·완독 일관)
                "objective": src.get("objective") or tmpl["objective"],
                "summary": src.get("summary") or tmpl["summary"],
            }
        )
    data["events"] = norm
    data["totalChaptersPlanned"] = total
    # world 가 문자열로 오면 dict 로 강제(다운스트림 .get 안전 — collab/집필 500 방지).
    world = data.get("world")
    if not isinstance(world, dict):
        data["world"] = {"setting": world} if isinstance(world, str) and world.strip() else {}
    # characters 는 dict 리스트로 정규화(항목이 문자열이면 name 으로).
    chars = data.get("characters")
    if not isinstance(chars, list):
        data["characters"] = []
    else:
        data["characters"] = [c if isinstance(c, dict) else {"name": str(c)} for c in chars]
    # secretArc 가 문자열로 오면 dict 로 강제(결말 장 폴백/집필/검수의 .get 안전 — 결말 500 방지).
    arc = data.get("secretArc")
    if not isinstance(arc, dict):
        data["secretArc"] = {"hidden": True, "outline": arc} if isinstance(arc, str) and arc.strip() else {}
    data.setdefault("learningObjectives", objectives)
    return data


async def build_bible(
    gemini: GeminiClient,
    prompt: PromptRecord | None,
    plan_messages: list[str],
    character_traits: list[str],
) -> dict[str, Any]:
    topic = prompt.topic if prompt else "자유 주제"
    objectives = prompt.learning_objectives if prompt else []
    total = DEFAULT_TOTAL_CHAPTERS

    if gemini.mock:
        return {
            "title": f"{topic} 이야기",
            "totalChaptersPlanned": total,
            "characters": [
                {
                    "id": "hero",
                    "name": "주인공",
                    "traits": character_traits or ["용감함"],
                    "appearance": "밝은 표정의 어린이",
                }
            ],
            "world": {"setting": f"{topic} 와(과) 관련된 친근한 세계", "tone": "따뜻하고 호기심 가득한"},
            "events": _distribute_objectives(objectives, total),
            "learningObjectives": objectives,
            # 후반 큰줄기: 아동 비공개. 집필/유도 단계 내부 참조용.
            "secretArc": {
                "hidden": True,
                "outline": "주인공이 배운 것을 스스로 적용해 문제를 해결하며 성장한다.",
            },
        }

    objectives_text = "\n".join(f"- {o}" for o in objectives)
    plan_text = "\n".join(f"- {m}" for m in plan_messages)
    instruction = (
        "너는 어린이 책 한 권의 설계자다. 아래 정보를 바탕으로 책의 Bible(JSON)을 만들어라. "
        "JSON 키: title, totalChaptersPlanned(int), characters[], world, events[], "
        "learningObjectives[], secretArc(후반 큰줄기, 아동 비공개). "
        "events 의 각 항목은 chapterIdx, mode(free|guided), objective, summary 를 가진다. "
        f"앞 절반은 free(자유), 뒤 절반은 guided(유도). 총 {total}개 챕터.\n\n"
        f"주제: {topic}\n학습목표:\n{objectives_text}\n기획 대화:\n{plan_text}\n\nJSON만 출력:"
    )
    raw = await gemini.generate_text(gemini.settings.gemini_model_pro, instruction)
    try:
        data = json.loads(_strip_code_fence(raw))
        # events 를 1..total 로 완전히 채우고 free/guided 분할 강제(이슈a 재발 방지).
        return _normalize_bible(data, objectives, total)
    except (json.JSONDecodeError, TypeError):
        # 파싱 실패 시 안전한 기본 Bible 로 폴백.
        return {
            "title": f"{topic} 이야기",
            "totalChaptersPlanned": total,
            "characters": [{"id": "hero", "name": "주인공", "traits": character_traits or ["용감함"]}],
            "world": {"setting": topic, "tone": "따뜻한"},
            "events": _distribute_objectives(objectives, total),
            "learningObjectives": objectives,
            "secretArc": {"hidden": True, "outline": ""},
        }


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.endswith("```"):
            t = t[: -3]
        if t.startswith("json"):
            t = t[4:]
    return t.strip()
