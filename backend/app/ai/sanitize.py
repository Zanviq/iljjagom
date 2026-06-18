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

# 본문 머리말/소제목(통째 생략): 마크다운 헤딩, "1장." 류 장 번호.
_HEADING = re.compile(r"^#{1,6}\s+")
_CHAPTER_HEADER = re.compile(r"^\d+\s*장\s*[.:、]?\s*$")


def strip_emoji(text: str | None) -> str:
    return _EMOJI.sub("", text or "")


def _strip_inline_md(s: str) -> str:
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)   # **굵게**
    s = re.sub(r"\*([^*]+)\*", r"\1", s)        # *기울임*
    s = re.sub(r"__([^_]+)__", r"\1", s)        # __강조__
    s = re.sub(r"`([^`]+)`", r"\1", s)          # `코드`
    return s.replace("**", "").replace("`", "").replace("#", "").replace("~~", "")


def sanitize_line(line: str | None) -> str | None:
    """본문 한 줄 정제.

    - 머리말/헤딩 줄("1장.", "## …")이면 ``None``(줄 통째 생략).
    - 빈 줄이면 ``""``(문단 구분 보존).
    - 그 외엔 인용·리스트 머리표와 인라인 마크다운을 제거한 평문.
    """
    s = strip_emoji(line or "")
    stripped = s.strip()
    if stripped == "":
        return ""
    if _HEADING.match(stripped) or _CHAPTER_HEADER.match(stripped):
        return None
    s = re.sub(r"^\s*>+\s*", "", s)      # 인용
    s = re.sub(r"^\s*[-*+]\s+", "", s)    # 불릿
    s = re.sub(r"^\s*\d+\.\s+", "", s)    # 번호 리스트
    return _strip_inline_md(s).rstrip()


def sanitize_body(text: str | None) -> str:
    """이야기 본문 전체 정제(저장·재생성 결과용). 머리말 줄 제거 + 인라인 마크다운 제거."""
    if not text:
        return ""
    out: list[str] = []
    for line in text.splitlines():
        c = sanitize_line(line)
        if c is None:
            continue
        out.append(c)
    t = "\n".join(out)
    t = re.sub(r"\n{3,}", "\n\n", t)     # 과도한 빈 줄 정리
    return t.strip()


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
