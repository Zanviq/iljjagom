"""08 실 퀴즈 생성 — 본문 기반 문항 파싱·학년 반영·폴백 강등 검증."""
from __future__ import annotations

from app.ai import quiz as quizgen
from app.ai.gemini import GeminiClient
from app.config import get_settings


class _FakeGemini:
    """실 모드(mock=False) 흉내 — generate_text 가 미리 정한 응답을 돌려준다."""

    mock = False

    def __init__(self, payload: str):
        self._payload = payload
        self.settings = get_settings()

    async def generate_text(self, model: str, prompt: str) -> str:
        self.last_prompt = prompt
        return self._payload


_TEMPLATE_MARK = "가장 관련 있는 것"  # 폴백 템플릿 문항의 표식


async def test_generate_quiz_parses_real_items():
    payload = (
        '```json\n{"quiz":[{"question":"토토는 물웅덩이에서 무엇을 보았나요?",'
        '"choices":["물이 줄어든 것","우주선","구구단"],"answerIndex":0},'
        '{"question":"물방울이 햇볕을 받으면 어떻게 되나요?",'
        '"choices":["사라진다","커진다","얼어붙는다"],"answerIndex":0}]}\n```'
    )
    fake = _FakeGemini(payload)
    quiz = await quizgen.generate_quiz(
        fake, story_text="토토가 물웅덩이의 물이 줄어든 걸 보았어요.",
        objectives=["증발"], grade=3, count=5, seed="b1",
    )
    assert len(quiz) == 2
    assert quiz[0].question.startswith("토토는")
    assert "구구단" in quiz[0].choices  # 모델 보기 사용(템플릿 아님)
    assert _TEMPLATE_MARK not in quiz[0].question
    assert quiz[0].answer_index == 0


async def test_generate_quiz_clamps_bad_answer_index_and_dedupes():
    payload = '{"quiz":[{"question":"Q","choices":["가","가","나"],"answerIndex":9}]}'
    fake = _FakeGemini(payload)
    quiz = await quizgen.generate_quiz(
        fake, story_text="본문", objectives=[], grade=5, count=5, seed="b2",
    )
    assert len(quiz) == 1
    assert quiz[0].choices == ["가", "나"]  # 중복 제거
    assert 0 <= quiz[0].answer_index < len(quiz[0].choices)  # 범위 밖 → 0 클램프


async def test_generate_quiz_falls_back_on_garbage():
    fake = _FakeGemini("퀴즈를 못 만들었어요(설명만)")
    quiz = await quizgen.generate_quiz(
        fake, story_text="본문", objectives=["증발", "응결"], grade=3, count=5, seed="b3",
    )
    # 파싱 실패 → 학습목표 템플릿으로 강등.
    assert len(quiz) == 2
    assert all(_TEMPLATE_MARK in q.question for q in quiz)


async def test_generate_quiz_mock_uses_template():
    g = GeminiClient()  # mock(키 없음)
    quiz = await quizgen.generate_quiz(
        g, story_text="본문", objectives=["증발"], grade=1, count=5, seed="b4",
    )
    assert len(quiz) == 1 and _TEMPLATE_MARK in quiz[0].question


async def test_generate_quiz_empty_story_uses_template():
    fake = _FakeGemini('{"quiz":[]}')
    quiz = await quizgen.generate_quiz(
        fake, story_text="   ", objectives=["증발"], grade=4, count=5, seed="b5",
    )
    assert len(quiz) == 1 and _TEMPLATE_MARK in quiz[0].question  # 본문 없으면 LLM 호출 안 함


def test_grade_guide_varies_by_grade():
    low = quizgen._grade_guide(1)
    mid = quizgen._grade_guide(3)
    high = quizgen._grade_guide(6)
    assert "1~2학년" in low and "3~4학년" in mid and "5~6학년" in high
    assert low != mid != high


async def test_generate_quiz_prompt_includes_grade_and_story():
    fake = _FakeGemini('{"quiz":[{"question":"Q","choices":["a","b"],"answerIndex":0}]}')
    await quizgen.generate_quiz(
        fake, story_text="토토와 개굴이 이야기", objectives=["증발"], grade=2, count=5, seed="b6",
    )
    # 프롬프트에 학년 지침·본문·학습주제가 실제로 들어갔는지.
    assert "1~2학년" in fake.last_prompt
    assert "토토와 개굴이 이야기" in fake.last_prompt
    assert "증발" in fake.last_prompt
