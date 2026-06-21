"""07 렌더링/로딩 최적화 회귀 — hot 읽기 경로의 Supabase 라운드트립(N+1) 방지.

books.get_book_detail / list_books 와 midactivity.get_mid_activity 가 챕터별 문단 조회나
bible 중복 조회를 하지 않고, 책 단위 일괄 조회(list_paragraphs_for_book)와 1회 bible 조회만
쓰는지 호출 횟수로 검증한다. 재발 시 즉시 실패.
"""
from __future__ import annotations

from collections import Counter

from app.deps import CurrentUser
from app.services import books, midactivity
from app.store import get_store


def _user(uid: str, role: str = "student") -> CurrentUser:
    return CurrentUser(id=uid, email=f"{uid}@x", role=role, profile=None, needs_onboarding=False)


class _CountingStore:
    """모든 메서드 호출을 세는 얇은 프록시(저장소 호출 횟수=라운드트립 근사)."""

    def __init__(self, inner):
        self._inner = inner
        self.calls: Counter[str] = Counter()

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if callable(attr):
            def wrapped(*a, **k):
                self.calls[name] += 1
                return attr(*a, **k)
            return wrapped
        return attr


def _make_book(store, kid: str) -> str:
    """기·승 3장(각 4문단 완료) + 전·결 3장(본문 有), 중간활동 완료한 done 책."""
    book = store.create_book(kid, None, None)
    events = [{"chapterIdx": i, "mode": "free"} for i in (1, 2, 3)]
    events += [{"chapterIdx": i, "mode": "guided"} for i in (4, 5, 6)]
    store.upsert_bible(book.id, {"title": "물의 순환", "totalChaptersPlanned": 6, "events": events})
    for i in (1, 2, 3):
        c = store.create_chapter(book.id, i, "free")
        for seq in range(1, 5):  # COLLAB_TARGET=4 문단 채워 완료
            store.add_paragraph(c.id, book.id, seq, f"문단{seq}")
        store.update_chapter(c.id, char_count=120)
    for i in (4, 5, 6):
        c = store.create_chapter(book.id, i, "guided")
        store.update_chapter(c.id, body="전결 본문", char_count=200)
    store.add_events(kid, [{"book_id": book.id, "type": midactivity.MID_DONE_EVENT, "payload": {}}])
    store.update_book(book.id, status="done", title="물의 순환", total_chapters_planned=6)
    return book.id


def test_get_book_detail_no_per_chapter_paragraph_queries():
    store = _CountingStore(get_store())
    kid = "kid-07a"
    book_id = _make_book(store, kid)
    store.calls.clear()

    detail = books.get_book_detail(store, _user(kid), book_id)

    # 6장이지만 문단은 책 단위 1회 일괄 조회만, 챕터별 조회는 0회.
    assert store.calls["list_paragraphs_for_book"] == 1
    assert store.calls["list_paragraphs"] == 0
    # 챕터 목록 1회, bible 1회(gate_blocked 내부 중복 제거).
    assert store.calls["list_chapters"] == 1
    assert store.calls["get_bible"] <= 1
    # 정합성: 문단수·이어가기 장 정상 계산.
    assert {c.idx: c.paragraph_count for c in detail.chapters if c.mode == "free"} == {1: 4, 2: 4, 3: 4}
    assert detail.current_chapter_idx == 6  # done → 마지막 장


def test_list_books_batches_per_book():
    store = _CountingStore(get_store())
    kid = "kid-07b"
    _make_book(store, kid)
    _make_book(store, kid)  # 같은 학생 2권
    store.calls.clear()

    res = books.list_books(store, _user(kid))

    assert len(res.books) == 2
    # 책당 문단 일괄 1회씩(=2), 챕터별 문단 조회 0회.
    assert store.calls["list_paragraphs_for_book"] == 2
    assert store.calls["list_paragraphs"] == 0
    # 책당 bible 1회 이하(2권 → <=2). 중복 조회 없음.
    assert store.calls["get_bible"] <= 2


def test_get_mid_activity_single_bible_fetch():
    store = _CountingStore(get_store())
    kid = "kid-07c"
    book_id = _make_book(store, kid)
    store.calls.clear()

    midactivity.get_mid_activity(store, _user(kid), book_id)

    # bible·챕터·문단을 1회씩만 조회(헬퍼 간 재사용).
    assert store.calls["get_bible"] == 1
    assert store.calls["list_paragraphs_for_book"] == 1
    assert store.calls["list_paragraphs"] == 0
