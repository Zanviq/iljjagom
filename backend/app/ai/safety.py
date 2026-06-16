"""안전 게이트 (P1 최소판) — 03-기능명세서 FR-X1.

- 입력: 부적절 표현 탐지 → 차단 + 안내(대체 표현 권유).
- 출력: 콘텐츠 안전 설정 적용(실 모델 호출 시) + 위험 신호 시 안내.
- 위험 신호는 safety_flags 로 기록(서비스 계층에서 store.add_safety_flag 호출).

P1은 키워드 기반 최소 구현. P4에서 모델 기반으로 강화.
"""
from __future__ import annotations

from dataclasses import dataclass

# 미성년 전제: 폭력/혐오/성적/자해 등 명백히 부적절한 표현(최소 사전).
_BLOCKLIST = [
    "죽여", "죽이", "자살", "씨발", "시발", "병신", "꺼져",
    "때려", "피흘", "칼로", "총으로",
]

# 정서 위험 신호(편지/대화에서 교사 확인이 필요한 신호).
_RISK_SIGNALS = ["죽고 싶", "사라지고 싶", "아무도 없", "혼자라서"]


@dataclass
class SafetyResult:
    ok: bool
    reason: str = ""
    suggestion: str = ""
    risk: bool = False  # 정서 위험 신호(보류/플래그 대상)


def check_input(text: str) -> SafetyResult:
    """학생 입력 검사. 부적절하면 ok=False + 안내."""
    lowered = text.replace(" ", "")
    risk = any(sig.replace(" ", "") in lowered for sig in _RISK_SIGNALS)
    for word in _BLOCKLIST:
        if word in lowered:
            return SafetyResult(
                ok=False,
                reason="부적절한 표현이 포함되어 있어요.",
                suggestion="조금 더 부드러운 말로 다시 표현해 볼까요?",
                risk=risk,
            )
    return SafetyResult(ok=True, risk=risk)


def filter_output(text: str) -> str:
    """AI 출력 후처리(P1 최소). 현재는 통과. 실 모델은 안전 설정으로 1차 차단."""
    return text
