"""학습 활동 서비스 — 어휘/퀴즈/독후감/감정 곡선 + 인물 편지 (FR-S8~S12).

책 본문/Bible 기반 자동 생성. mock 에서는 결정적으로 책에서 파생한다.
편지는 정서 위험 신호 시 답장 보류(held) + safety_flags 기록.
"""
from __future__ import annotations

from app.ai import chat
from app.ai.gemini import GeminiClient
from app.ai.safety import check_input
from app.deps import CurrentUser
from app.errors import validation_error
from app.models.schemas import (
    EmotionPoint,
    EssayBlank,
    LearningResponse,
    LetterResponse,
    QuizItem,
    Word,
)
from app.services import words
from app.services.books import assert_can_access_book, assert_owner_student, get_book_or_404
from app.store.base import Store

# 감정 곡선 라벨(기승전결 흐름). 챕터 진행도에 매핑.
_EMOTION_LABELS = ["설렘", "호기심", "긴장", "용기", "감동", "뿌듯함"]


async def build_learning(
    store: Store, gemini: GeminiClient, user: CurrentUser, book_id: str
) -> LearningResponse:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)

    chapters = [c for c in store.list_chapters(book_id) if c.char_count > 0]
    bible_rec = store.get_bible(book_id)
    bible = bible_rec.data if bible_rec else {}

    # 1) 어휘 카드: 집필된 챕터의 단어 후보(중복 제거, 최대 8) → 뜻풀이.
    terms: list[str] = []
    for c in chapters:
        for w in c.words:
            if w not in terms:
                terms.append(w)
    # 뜻풀이는 외부 AI 호출이라 일시 오류(503)가 날 수 있다 → 실패한 단어는 건너뛰고
    # 나머지 학습 활동(quiz/essay/emotion)은 그대로 제공(부분 강등).
    vocab: list[Word] = []
    for t in terms[:8]:
        try:
            vocab.append(await words.lookup(gemini, t))
        except Exception:
            continue

    # 2) 퀴즈: 학습목표(이벤트별 objective, 없으면 발제 목표)에서 생성.
    objectives = [e.get("objective") for e in bible.get("events", []) if e.get("objective")]
    if not objectives and book.prompt_id:
        prompt = store.get_prompt(book.prompt_id)
        objectives = list(prompt.learning_objectives) if prompt else []
    quiz: list[QuizItem] = []
    for obj in objectives[:5]:
        quiz.append(
            QuizItem(
                question=f"이 이야기에서 '{obj}'와(과) 가장 관련 있는 것은 무엇일까요?",
                choices=[f"{obj}을(를) 보여주는 장면", "이야기와 관계없는 이야기", "전혀 다른 과목 내용"],
                answer_index=0,
            )
        )

    # 3) 독후감 빈칸: 인물/제목 기반 일반 프롬프트.
    char_names = [c.get("name", "") for c in bible.get("characters", []) if c.get("name")]
    essay_blanks: list[EssayBlank] = [
        EssayBlank(
            prompt="이 이야기에서 가장 기억에 남는 장면은 무엇이고, 왜 그런가요?",
            hints=char_names[:3] or ["주인공", "사건"],
        ),
        EssayBlank(
            prompt="내가 주인공이었다면 어떻게 했을까요?",
            hints=["나의 선택", "그 이유"],
        ),
    ]

    # 4) 감정 곡선: 집필된 챕터 순서대로 결정적 값.
    total = bible.get("totalChaptersPlanned") or len(chapters) or 1
    emotion: list[EmotionPoint] = []
    for c in chapters:
        label = _EMOTION_LABELS[(c.idx - 1) % len(_EMOTION_LABELS)]
        value = round(min(0.95, 0.3 + 0.6 * (c.idx / total)), 2)
        emotion.append(EmotionPoint(chapter_idx=c.idx, label=label, value=value))

    return LearningResponse(
        vocab=vocab, quiz=quiz, essay_blanks=essay_blanks, emotion=emotion
    )


async def write_letter(
    store: Store,
    gemini: GeminiClient,
    user: CurrentUser,
    book_id: str,
    to: str,
    body: str,
) -> LetterResponse:
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book)

    # 안전 게이트: 부적절/정서 위험 신호 시 답장 보류 + 교사 확인.
    # 보류 편지는 원문을 letters 에 저장하고 safety_flags 와 연결해 교사 검토로 종결한다.
    safety = check_input(body)
    if not safety.ok or safety.risk:
        letter = store.add_letter(book_id, user.id, to, body, status="held")
        severity = "high" if safety.risk else "normal"
        store.add_safety_flag(
            book_id, user.id, "letter",
            safety.reason or "정서 위험 신호 감지",
            category=getattr(safety, "category", None),
            severity=severity,
            letter_id=letter.id,
        )
        # 학습결과(편지)도 함께 기록(04 측정 — 신규 엔드포인트 불필요).
        store.add_learning_artifact(
            book_id, "letter",
            {"to": to, "body": body, "status": "held", "replySaved": False},
        )
        return LetterResponse(status="held", reply=None, letter_id=letter.id)

    bible_rec = store.get_bible(book_id)
    characters = bible_rec.data.get("characters", []) if bible_rec else []
    character = next((c for c in characters if c.get("name") == to), None)
    if not character:
        raise validation_error("그 인물을 찾을 수 없어요.", {"field": "to"})

    reply = await chat.persona_reply(
        gemini, character.get("name", to), character.get("traits", []), body
    )
    letter = store.add_letter(
        book_id, user.id, to, body, status="answered", reply=reply, reply_source="ai"
    )
    store.add_learning_artifact(
        book_id, "letter", {"to": to, "body": body, "status": "answered", "replySaved": True}
    )
    return LetterResponse(status="answered", reply=reply, letter_id=letter.id)
