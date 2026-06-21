"""실 퀴즈 생성 — 본문 내용·학습목표·학년 수준을 반영한 객관식 문항(Gemini).

기존 퀴즈는 본문을 읽지 않는 템플릿("이야기와 관계없는 이야기" 같은 더미 보기)이라 진짜
독해 평가가 아니었고 학년 수준도 무시했다. 본 모듈은 실제 본문을 읽혀 내용 이해 + 학습목표
적용 문항을 학년 난이도에 맞춰 만든다. mock/실패 시 결정적 템플릿(build_template_quiz)으로
강등해 학습 흐름을 끊지 않는다(부분 강등 원칙).
"""
from __future__ import annotations

import json
import random
from typing import Any

from app.ai.gemini import GeminiClient
from app.models.schemas import QuizItem

MAX_STORY_CHARS = 4000  # 프롬프트에 넣는 본문 상한(토큰·비용 가드)
MAX_CHOICES = 4


def _make_quiz_item(obj: str, seed_key: str) -> QuizItem:
    """정답 위치를 결정적(seed)으로 셔플한 템플릿 문항(학생/10). 폴백·mock 전용."""
    correct = f"{obj}을(를) 보여주는 장면"
    choices = [correct, "이야기와 관계없는 이야기", "전혀 다른 과목 내용"]
    random.Random(seed_key).shuffle(choices)
    return QuizItem(
        question=f"이 이야기에서 '{obj}'와(과) 가장 관련 있는 것은 무엇일까요?",
        choices=choices,
        answer_index=choices.index(correct),
    )


def build_template_quiz(objectives: list[str], seed: str, count: int = 5) -> list[QuizItem]:
    """학습목표 기반 결정적 템플릿 퀴즈(폴백). 정답 인덱스 쏠림 가드 포함."""
    objs = [o for o in objectives if o][:count]
    quiz = [_make_quiz_item(o, f"{seed}:{i}") for i, o in enumerate(objs)]
    if len(quiz) > 1 and len({q.answer_index for q in quiz}) == 1:
        last = quiz[-1]
        rot = (last.answer_index + 1) % len(last.choices)
        last.choices[last.answer_index], last.choices[rot] = (
            last.choices[rot], last.choices[last.answer_index],
        )
        last.answer_index = rot
    return quiz


def _grade_guide(grade: int | None) -> str:
    """학년대별 난이도·낱말 지침 문장."""
    if grade is None:
        grade = 3
    if grade <= 2:
        return (
            "초등 1~2학년 수준. 아주 쉬운 낱말과 짧은 문장을 쓴다. 이야기에 '직접 나온' 사실만 "
            "묻고, 어려운 개념어나 복잡한 추론은 내지 않는다."
        )
    if grade <= 4:
        return (
            "초등 3~4학년 수준. 쉬운 낱말을 쓴다. 이야기 속 사실 확인과 함께 인물의 마음·행동의 "
            "까닭을 묻는 간단한 추론을 섞는다."
        )
    return (
        "초등 5~6학년 수준. 이야기 내용을 바탕으로 추론하고, 학습 주제(개념)를 이야기 상황에 "
        "적용해 설명하는 문항을 낸다."
    )


def _normalize(items: Any, count: int) -> list[QuizItem]:
    """모델 출력(list[dict])을 검증된 QuizItem 목록으로. 잘못된 항목은 건너뛴다."""
    out: list[QuizItem] = []
    if not isinstance(items, list):
        return out
    for it in items:
        if not isinstance(it, dict):
            continue
        q = str(it.get("question", "")).strip()
        raw_choices = it.get("choices")
        if not q or not isinstance(raw_choices, list):
            continue
        # 보기 정제 + 중복 제거(순서 보존).
        seen: set[str] = set()
        choices: list[str] = []
        for c in raw_choices:
            s = str(c).strip()
            if s and s not in seen:
                seen.add(s)
                choices.append(s)
        choices = choices[:MAX_CHOICES]
        if len(choices) < 2:
            continue
        try:
            ai = int(it.get("answerIndex", it.get("answer_index", 0)))
        except (TypeError, ValueError):
            ai = 0
        if not (0 <= ai < len(choices)):
            ai = 0
        out.append(QuizItem(question=q, choices=choices, answer_index=ai))
        if len(out) >= count:
            break
    return out


def _strip_json(raw: str) -> str:
    """코드블록·잡설을 벗기고 첫 { … 마지막 } 만 남긴다(관대한 JSON 추출)."""
    t = (raw or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.endswith("```"):
            t = t[:-3]
        if t.startswith("json"):
            t = t[4:]
    t = t.strip()
    if not t.startswith("{"):
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1 and e > s:
            t = t[s : e + 1]
    return t


async def generate_quiz(
    gemini: GeminiClient,
    *,
    story_text: str,
    objectives: list[str],
    grade: int | None,
    count: int = 5,
    seed: str,
) -> list[QuizItem]:
    """본문·학습목표·학년 수준을 반영한 객관식 퀴즈를 만든다.

    실 Gemini 로 내용 이해 + 학습목표 적용 문항을 생성하고, mock/본문없음/실패 시
    템플릿(build_template_quiz)으로 강등한다.
    """
    objs = [o for o in objectives if o]
    story = (story_text or "").strip()
    if gemini.mock or not story:
        return build_template_quiz(objs, seed, count)

    obj_line = (
        "학습 주제(이 중 일부를 문항에 자연스럽게 녹인다): " + ", ".join(objs) + "\n" if objs else ""
    )
    prompt = (
        "너는 어린이 독서 교육 전문가다. 아래 '이야기 본문'을 읽고, 아이가 내용을 잘 이해했는지 "
        "확인하는 객관식 퀴즈를 만든다.\n"
        f"- 대상: {_grade_guide(grade)}\n"
        f"- 문항 수: 정확히 {count}개.\n"
        "- 각 문항의 보기는 3개. 정답은 반드시 본문 내용과 일치해야 하고, 오답도 그럴듯하지만 "
        "본문과 다른 내용으로 만든다. '이야기와 관계없는 내용', '다른 과목 내용' 같은 엉뚱한 "
        "보기는 절대 쓰지 않는다.\n"
        "- 이야기 속 인물·사건·까닭을 묻는 '내용 이해' 문항과 위 학습 주제를 이야기 상황에 "
        "연결하는 문항을 섞는다.\n"
        "- 정답 위치(answerIndex)는 0,1,2 에 골고루 분산한다.\n"
        "- 이야기의 결말을 직접 누설하는 문항은 피한다.\n"
        "아래 JSON 하나만 출력한다(설명·코드블록 금지). answerIndex 는 0부터 시작하는 정답 보기 번호.\n"
        '{"quiz":[{"question":"...","choices":["...","...","..."],"answerIndex":0}]}\n\n'
        f"{obj_line}이야기 본문:\n{story[:MAX_STORY_CHARS]}\n\nJSON:"
    )
    try:
        raw = await gemini.generate_text(gemini.settings.gemini_model_flash, prompt)
        data = json.loads(_strip_json(raw))
        items = data.get("quiz") if isinstance(data, dict) else data
        quiz = _normalize(items, count)
        if quiz:
            return quiz
    except Exception:
        pass
    return build_template_quiz(objs, seed, count)
