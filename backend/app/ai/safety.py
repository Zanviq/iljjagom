"""안전 게이트 — 입력 카테고리화 + 출력(무거운 장면) 점검. 03-기능명세서 FR-X1, 추가기능 03 §3.

- 입력: 부적절 표현 카테고리 탐지 → 차단 + 안내. 정서 위험 신호 → risk(보류 대상).
- 출력: 무거운 장면(죽음/유기/유혈) 신호 탐지 → 교사 사후 확인용 플래그(학생 흐름은 막지 않음).
- 모델 콘텐츠 안전 설정은 gemini.py 에서 safety_settings 로 적용.
키워드 기반 1차 게이트 + 정규화. 정밀화는 check_safety 스킬(02)/모델 2차 판정.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 미성년 전제: 카테고리별 부적절 표현(최소 사전). 정규화(공백 제거) 후 부분일치.
_CATEGORY_BLOCKLIST: dict[str, list[str]] = {
    "violence": ["죽여", "죽이", "때려", "패버", "피흘", "칼로", "총으로"],
    "profanity": ["씨발", "시발", "병신", "꺼져", "지랄"],
    "sexual": ["섹스", "야동"],
    "self_harm": ["자살", "자해"],
}

# 정서 위험 신호(편지/대화에서 교사 확인이 필요한 신호) — 차단이 아니라 보류(held).
_RISK_SIGNALS = [
    "죽고 싶", "사라지고 싶", "아무도 없", "혼자라서", "외로워",
    "너무 외로", "살기 싫", "다 싫어", "포기하고 싶",
]

# 출력 무거운 장면 신호(순화/교사 확인 대상). 자유 집필 출력에서 사후 확인.
_HEAVY_SCENE_SIGNALS = ["죽었", "죽임", "피가 흘", "버려졌", "버림받", "목을 매", "사라져 버"]


@dataclass
class SafetyResult:
    ok: bool
    reason: str = ""
    suggestion: str = ""
    risk: bool = False  # 정서 위험 신호(보류/플래그 대상)
    category: str | None = None  # violence|profanity|sexual|self_harm


@dataclass
class OutputSafetyResult:
    ok: bool
    filtered_text: str
    softened: bool = False
    flags: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    # 공백·반복문자 정규화(우회 완화). 자모/유사문자 정밀화는 후속.
    t = re.sub(r"\s+", "", text)
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)  # 3연속 이상 반복 → 2개로
    return t


def check_input(text: str) -> SafetyResult:
    """학생 입력 검사. 부적절하면 ok=False + 카테고리/안내. 정서 위험은 risk=True."""
    normalized = _normalize(text)
    risk = any(_normalize(sig) in normalized for sig in _RISK_SIGNALS)
    for category, words in _CATEGORY_BLOCKLIST.items():
        for word in words:
            if word in normalized:
                return SafetyResult(
                    ok=False,
                    reason="부적절한 표현이 포함되어 있어요.",
                    suggestion="조금 더 부드러운 말로 다시 표현해 볼까요?",
                    risk=risk,
                    category=category,
                )
    return SafetyResult(ok=True, risk=risk)


def filter_output(
    text: str, *, grade: int | None = None, safety_level: str = "strict"
) -> OutputSafetyResult:
    """AI 출력 후처리 — 무거운 장면 신호를 탐지해 플래그(학생 흐름은 막지 않는다).

    본문은 보존(학생 콘텐츠 훼손 방지). 신호가 있으면 호출자가 safety_flags(source=output)로 기록.
    """
    normalized = _normalize(text)
    flags = [sig for sig in _HEAVY_SCENE_SIGNALS if sig in normalized]
    softened = bool(flags) and safety_level == "strict"
    return OutputSafetyResult(ok=True, filtered_text=text, softened=softened, flags=flags)
