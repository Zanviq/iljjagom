"""자유집필(기·승, free) 협업 프롬프트용 Bible 브리프.

설계(Bible)의 인물·세계·현재 장 목표를 집필 프롬프트에 주입해, 곰 작가가 이미 정한
설정을 반영하도록 한다(05-기능수정 §01).

엄수: secretArc(후반 큰줄기)·뒤 절반(guided) 사건은 **절대 포함하지 않는다**. 이 함수는
현재 장 event 하나만 받아 그 목표·줄거리만 노출하며, secretArc 키는 어떤 경우에도 읽지 않는다.
"""
from __future__ import annotations

from typing import Any


def bible_brief(bible: dict[str, Any], event: dict[str, Any] | None = None) -> str:
    """기·승 협업용 설정 브리프 문자열. 노출할 게 없으면 빈 문자열."""
    if not isinstance(bible, dict):
        return ""
    lines: list[str] = []

    chars = bible.get("characters") or []
    if isinstance(chars, list):
        parts: list[str] = []
        for c in chars:
            if not isinstance(c, dict):
                continue
            name = (c.get("name") or "").strip()
            if not name:
                continue
            traits = c.get("traits") or []
            trait_txt = (
                ", ".join(str(t) for t in traits if t)
                if isinstance(traits, list)
                else str(traits)
            )
            parts.append(f"{name}({trait_txt})" if trait_txt else name)
        if parts:
            lines.append("인물: " + " · ".join(parts))

    world = bible.get("world") or {}
    if isinstance(world, dict):
        wbits = [
            world[k].strip()
            for k in ("setting", "place", "tone", "details")
            if isinstance(world.get(k), str) and world[k].strip()
        ]
        if wbits:
            lines.append("세계: " + " / ".join(wbits))

    objs = bible.get("learningObjectives") or []
    if isinstance(objs, list):
        obj_txt = ", ".join(str(o) for o in objs if o)
        if obj_txt:
            lines.append("학습목표: " + obj_txt)

    # 현재 장 event 만 노출(뒤 절반·secretArc 차단).
    if isinstance(event, dict):
        cur: list[str] = []
        if event.get("objective"):
            cur.append(f"이번 장 목표: {event['objective']}")
        if event.get("summary"):
            cur.append(f"이번 장 줄거리: {event['summary']}")
        if cur:
            lines.append(" / ".join(cur))

    if not lines:
        return ""
    return "[이야기 설정]\n" + "\n".join(lines)
