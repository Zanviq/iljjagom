"""총괄(overseer) AI 가 생성하는 navigate 액션의 라우트 화이트리스트.

총괄 AI 는 임의 URL 로 보낼 수 없다(03-총괄AI-사이드바 §5 보안). 학생 비몰입 화면만 허용:
- /home               메인 허브(기본)
- /learn[/...]        학습 활동
- /books/new[?promptId=…]  책 만들기(프론트 발제 선택)
- /books/{uuid}/plan  기획 페이지
- /books/{uuid}/read  독서 페이지

plan/read 도 라우트로는 허용한다(특정 책 열기 액션). 단 FAB/드로어 노출 게이팅(plan/read 제외)은
프론트 책임이다(백엔드는 이동 액션만 생성).
"""
from __future__ import annotations

import re

_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_PROMPT_ID = r"[0-9a-fA-F-]{1,64}"

_ALLOWED = [
    re.compile(r"^/home$"),
    re.compile(r"^/learn(?:/[\w-]+)*$"),
    re.compile(rf"^/books/new(?:\?promptId={_PROMPT_ID})?$"),
    re.compile(rf"^/books/{_UUID}/plan$"),
    re.compile(rf"^/books/{_UUID}/read$"),
]


def is_allowed_route(to: str) -> bool:
    """to 가 허용 라우트(상대 경로)인지. 외부 URL·프로토콜·`//` 는 거부."""
    if not to or not isinstance(to, str):
        return False
    if not to.startswith("/") or to.startswith("//"):
        return False
    if "://" in to:
        return False
    return any(p.match(to) for p in _ALLOWED)


def route_for_book(status: str | None, book_id: str) -> str:
    """책 상태에 맞는 이동 경로. planning 이면 기획, 그 외(writing/done)는 독서."""
    if status == "planning":
        return f"/books/{book_id}/plan"
    return f"/books/{book_id}/read"
