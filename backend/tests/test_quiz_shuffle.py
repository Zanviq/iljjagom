"""퀴즈 정답 위치 무작위화(학생/10) — 분산·결정성·정답 인덱스 정합."""
from __future__ import annotations

from app.services.learning import _build_quiz, _make_quiz_item


def test_answer_index_matches_correct_choice():
    objs = ["증발", "응결", "강수", "순환", "저장"]
    for q in _build_quiz(objs, "book-xyz"):
        correct = next(c for c in q.choices if c.endswith("을(를) 보여주는 장면"))
        assert q.choices[q.answer_index] == correct


def test_answer_index_not_all_same():
    objs = ["증발", "응결", "강수", "순환", "저장"]
    quiz = _build_quiz(objs, "book-xyz")
    assert len({q.answer_index for q in quiz}) >= 2  # 전부 0(고정) 아님


def test_answer_index_deterministic_per_book():
    objs = ["증발", "응결", "강수"]
    a = [q.answer_index for q in _build_quiz(objs, "book-A")]
    b = [q.answer_index for q in _build_quiz(objs, "book-A")]
    assert a == b  # 같은 book_id 재호출 시 동일(캐싱·mock 결정성)


def test_answer_index_varies_across_books():
    objs = ["증발", "응결", "강수", "순환", "저장"]
    a = [q.answer_index for q in _build_quiz(objs, "book-A")]
    b = [q.answer_index for q in _build_quiz(objs, "book-B")]
    assert a != b  # 책마다 위치 분산(시드 차이)


def test_skew_guard_single_item():
    # 문항 1개면 가드가 강제 회전하지 않고 정답 정합만 유지.
    q = _make_quiz_item("증발", "book-A:0")
    assert q.choices[q.answer_index].endswith("을(를) 보여주는 장면")
