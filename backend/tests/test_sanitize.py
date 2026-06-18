"""본문/답변 정제(학생/08·16) — 마크다운·머리말·이모지 제거, 문단 보존."""
from __future__ import annotations

from app.ai.sanitize import sanitize_body, sanitize_line, sanitize_reply, strip_emoji


def test_strip_emoji():
    assert strip_emoji("좋아 😊👍") == "좋아 "
    assert strip_emoji("국기 🇰🇷 별 ⭐") == "국기  별 "


def test_sanitize_line_drops_headers():
    assert sanitize_line("1장.") is None
    assert sanitize_line("## 소제목") is None
    assert sanitize_line("3 장") is None
    assert sanitize_line("") == ""          # 빈 줄(문단 구분) 보존
    assert sanitize_line("   ") == ""


def test_sanitize_line_strips_inline_and_markers():
    assert sanitize_line("**굵게** 보통") == "굵게 보통"
    assert sanitize_line("- 목록 항목") == "목록 항목"
    assert sanitize_line("> 인용문") == "인용문"
    assert sanitize_line("`코드` 끝") == "코드 끝"


def test_sanitize_body_removes_markdown_and_headers():
    raw = "1장.\n**토끼**가 달렸어요.\n\n## 다음 장면\n- 숲으로 갔어요."
    out = sanitize_body(raw)
    assert "1장." not in out
    assert "**" not in out and "#" not in out and "- " not in out
    assert "토끼가 달렸어요." in out
    assert "숲으로 갔어요." in out


def test_sanitize_body_preserves_paragraph_breaks():
    raw = "첫 문단입니다.\n\n둘째 문단입니다."
    out = sanitize_body(raw)
    assert out == "첫 문단입니다.\n\n둘째 문단입니다."


def test_sanitize_body_collapses_extra_blank_lines():
    raw = "가나다.\n\n\n\n라마바."
    assert sanitize_body(raw) == "가나다.\n\n라마바."


def test_sanitize_reply_unaffected_by_body_helpers():
    # reply 정제는 한 줄로(대화용), body 정제는 줄 구조 보존.
    assert sanitize_reply("**안녕** 😊\n반가워") == "안녕 반가워"
