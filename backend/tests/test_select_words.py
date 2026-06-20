"""낱말 선정 품질(학생/05) — 표제어화·불용어/고유명사 제외·학년 난이도·상위 N."""
from __future__ import annotations

from app.ai.writer import _lemma, select_words

TEXT = "별이는 깊은 계곡에 도착했어요. 초록산 너머로 따스한 바람이 불었어요. 신비한 보물을 찾았어요."


def test_lemma_strips_josa():
    assert _lemma("계곡에") == "계곡"
    assert _lemma("보물을") == "보물"
    assert _lemma("바람이") == "바람"
    assert _lemma("별이는") == "별이"
    assert _lemma("계곡") == "계곡"  # 조사 없으면 그대로


def test_select_words_strips_josa_and_caps():
    words = select_words(TEXT)
    assert len(words) <= 5
    assert "계곡에" not in words and "보물을" not in words and "바람이" not in words
    assert "계곡" in words or "보물" in words  # 표제어로 선정


def test_select_words_excludes_stopwords():
    words = select_words("이야기 이야기 계곡에 보물을 신비한 모험을")
    assert "이야기" not in words  # 빈출 기능어 제외


def test_select_words_excludes_proper_nouns():
    words = select_words(TEXT, exclude=["초록산", "별이"])
    assert "초록산" not in words and "별이" not in words


def test_proper_nouns_includes_title_tokens():
    from app.ai.writer import proper_nouns

    pn = proper_nouns({"title": "우당탕탕 초록산 대작전", "characters": [{"name": "별이"}]})
    assert "초록산" in pn and "별이" in pn and "대작전" in pn


def test_select_words_excludes_title_proper_noun():
    from app.ai.writer import proper_nouns

    bible = {"title": "우당탕탕 초록산 대작전", "characters": [{"name": "별이"}]}
    words = select_words(TEXT, exclude=proper_nouns(bible))
    assert "초록산" not in words  # 제목 속 지명은 낱말 후보에서 제외(이슈1)


def test_select_words_grade_band():
    text = "보물 계곡 모험 우정 약속 신비한 아름다운"
    g6 = select_words(text, grade=6)
    g1 = select_words(text, grade=1)
    assert all(len(w) >= 3 for w in g6)         # 고학년: 짧은(쉬운) 단어 배제
    assert any(len(w) == 2 for w in g1)         # 저학년: 2글자 단어 허용
