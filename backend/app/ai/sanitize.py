"""AI 출력 정제 — 이모지·마크다운·작업 흔적 제거(브랜드 규칙: 이모지 금지).

학생/08(본문)·학생/16(총괄 AI reply) 공통 유틸. 한 곳에서 정제한다.
- ``strip_emoji``: 이모지/기호 픽토그램 제거.
- ``sanitize_reply``: 짧은 대화 답변용(이모지·인라인 마크다운·머리표 제거 + 공백 정리, 한 줄로).
"""
from __future__ import annotations

import re

# 이모지/픽토그램/지역표시/변형선택자/ZWJ 범위. 😊(U+1F60A) 포함.
_EMOJI = re.compile(
    "["
    "\U0001f300-\U0001faff"  # 그림문자·이모티콘·교통·기호 확장
    "\U0001f1e6-\U0001f1ff"  # 지역 표시(국기)
    "\U00002600-\U000027bf"  # 기타 기호·딩벳
    "\U00002b00-\U00002bff"  # 별·화살표 등
    "\U0000fe00-\U0000fe0f"  # 변형 선택자
    "\U00002190-\U000021ff"  # 화살표
    "\U0000200d"             # ZWJ
    "]+",
    flags=re.UNICODE,
)

# 인라인 마크다운 기호(강조·코드·헤딩·취소선).
_MD_INLINE = re.compile(r"[*`#~]")


def strip_emoji(text: str | None) -> str:
    return _EMOJI.sub("", text or "")


def sanitize_reply(text: str | None) -> str:
    """곰 작가 reply 등 짧은 답변 정제: 이모지·마크다운 제거 후 한 줄 평문."""
    t = strip_emoji(text or "")
    lines: list[str] = []
    for line in t.splitlines():
        s = line.strip()
        s = re.sub(r"^>+\s*", "", s)        # 인용 머리표
        s = re.sub(r"^[-*+]\s+", "", s)      # 불릿
        s = re.sub(r"^\d+\.\s+", "", s)      # 번호 리스트
        if s:
            lines.append(s)
    t = " ".join(lines)
    t = _MD_INLINE.sub("", t)                # 인라인 기호
    t = re.sub(r"\s+", " ", t).strip()
    return t
