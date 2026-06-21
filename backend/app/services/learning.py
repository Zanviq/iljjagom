"""학습 활동 서비스 — 어휘/퀴즈/독후감/감정 곡선 + 인물 편지 (FR-S8~S12).

책 본문/Bible 기반 자동 생성. mock 에서는 결정적으로 책에서 파생한다.
편지는 정서 위험 신호 시 답장 보류(held) + safety_flags 기록.
"""
from __future__ import annotations

import asyncio

from app.ai import chat
from app.ai import quiz as quizgen
from app.ai.gemini import GeminiClient
from app.ai.quiz import _make_quiz_item  # noqa: F401 — 하위호환 재노출(test_quiz_shuffle)
from app.ai.safety import check_input
from app.ai.sanitize import sanitize_body
from app.deps import CurrentUser
from app.errors import validation_error
from app.models.schemas import (
    EmotionFrame,
    EmotionPoint,
    EssayBlank,
    LearningResponse,
    LetterCharacter,
    LetterResponse,
    QuizItem,
    Word,
    serialize,
)
from app.services import words
from app.services.books import assert_can_access_book, assert_owner_student, get_book_or_404
from app.services.prefetch import acquire_prefetch, release_prefetch
from app.store.base import Store

# 감정 팔레트(학생/11 입력 활동). 학생이 장마다 직접 고른다.
_EMOTION_LABELS = ["설렘", "호기심", "긴장", "용기", "슬픔", "감동", "뿌듯함"]


def _build_quiz(objectives: list[str], book_id: str) -> list[QuizItem]:
    """하위호환 래퍼 — 결정적 템플릿 퀴즈(폴백·mock). 실 퀴즈는 quizgen.generate_quiz."""
    return quizgen.build_template_quiz(objectives, book_id)


def _story_text(chapters: list) -> str:
    """본문(장별)을 이어 퀴즈 생성용 텍스트로. 자유 챕터도 chapters.body 가 재조립돼 있다."""
    parts: list[str] = []
    for c in chapters:
        body = sanitize_body(c.body).strip() if c.body else ""
        if body:
            parts.append(f"[{c.idx}장]\n{body}")
    return "\n\n".join(parts)


LEARNING_SET = "learning_set"  # 생성 교재 캐시(학생 자기보고 결과와 구분)


# 캐시 스키마 버전 — 생성 로직이 바뀌면(예: 템플릿→실 AI 퀴즈, 07) 올려서 옛 캐시를 무효화한다.
# v2: 본문 기반·학년 맞춤 실 AI 퀴즈 도입(고정 템플릿 캐시 폐기).
_CACHE_VERSION = "v2"


def _source_sig(chapters: list) -> str:
    """캐시 키 — 버전 + 학생 진입 챕터의 idx:char_count. 추가 집필·revise·버전업 시 자동 무효화."""
    return _CACHE_VERSION + "|" + "|".join(f"{c.idx}:{c.char_count}" for c in chapters)


async def build_learning(
    store: Store, gemini: GeminiClient, user: CurrentUser, book_id: str
) -> LearningResponse:
    """학습 교재: 집필 챕터 시그니처 기준 1회 생성·영속화(learning_set) → 재방문 즉시(학생/13)."""
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)

    # 선생성(prefetch)만 된 미진입 챕터는 학습활동 대상에서 제외(읽지 않은 앞선 내용 차단, 학생/06).
    chapters = [
        c for c in store.list_chapters(book_id)
        if c.char_count > 0 and not getattr(c, "prefetched", False)
    ]
    sig = _source_sig(chapters)

    # 1) 캐시 조회: 같은 sig 의 learning_set 가 있으면 어휘 LLM 호출 없이 즉시 반환.
    #    (구버전 스냅샷 형태는 검증 실패 시 무시하고 재생성 — emotion 객체화 등 스키마 진화 안전.)
    if chapters:
        for a in store.list_learning_artifacts(book_id=book_id, type=LEARNING_SET):
            if a.data.get("sourceSig") == sig:
                payload = {k: v for k, v in a.data.items() if k != "sourceSig"}
                try:
                    return LearningResponse.model_validate(payload)
                except Exception:
                    break  # 형태 불일치 → 재생성

    # 2) 미스 → 생성.
    result = await _generate_learning(store, gemini, book, chapters)

    # 3) 저장(스냅샷). 빈 책은 캐시하지 않음(다음 집필 후 재생성 유도).
    if chapters:
        try:
            store.add_learning_artifact(book_id, LEARNING_SET, {"sourceSig": sig, **serialize(result)})
        except Exception:
            pass
    return result


async def prefetch_learning(store: Store, gemini: GeminiClient, book_id: str) -> None:
    """결(마지막 장) 완료 직후 마무리 학습 교재(어휘·실 퀴즈 등)를 백그라운드 생성·캐시.

    학생이 '학습하러 가기' 를 누르기 전에 미리 만들어, 실 AI 퀴즈 생성 지연을 대기에서 없앤다.
    멱등·단일성(이미 최신 캐시면 skip).
    """
    book = store.get_book(book_id)
    if not book:
        return
    chapters = [
        c for c in store.list_chapters(book_id)
        if c.char_count > 0 and not getattr(c, "prefetched", False)
    ]
    if not chapters:
        return
    sig = _source_sig(chapters)
    for a in store.list_learning_artifacts(book_id=book_id, type=LEARNING_SET):
        if a.data.get("sourceSig") == sig:
            return  # 이미 준비됨
    if not acquire_prefetch(book_id, "learning"):
        return
    try:
        result = await _generate_learning(store, gemini, book, chapters)
        try:
            store.add_learning_artifact(book_id, LEARNING_SET, {"sourceSig": sig, **serialize(result)})
        except Exception:
            pass
    except Exception:
        pass
    finally:
        release_prefetch(book_id, "learning")


async def _generate_learning(
    store: Store, gemini: GeminiClient, book, chapters: list
) -> LearningResponse:
    book_id = book.id
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
    # 병렬 호출(학생/10): 8회 직렬 대기 → gather 로 체감 딜레이 완화. 순서 보존.
    results = await asyncio.gather(
        *(words.lookup(gemini, t) for t in terms[:8]), return_exceptions=True
    )
    vocab: list[Word] = [r for r in results if isinstance(r, Word)]

    # 2) 퀴즈: 본문 내용 이해 + 학습목표 적용을 학년 수준에 맞춰 실 생성(실패 시 템플릿 강등).
    objectives = [e.get("objective") for e in bible.get("events", []) if e.get("objective")]
    if not objectives and book.prompt_id:
        prompt = store.get_prompt(book.prompt_id)
        objectives = list(prompt.learning_objectives) if prompt else []
    from app.services import policy

    grade = policy.resolve_grade(store, book=book)
    quiz = await quizgen.generate_quiz(
        gemini,
        story_text=_story_text(chapters),
        objectives=[o for o in objectives if o],
        grade=grade,
        count=5,
        seed=book_id,
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

    # 4) 감정 곡선: 시스템 자동 곡선 제거 → 학생 입력 틀(장 목록 + 라벨 팔레트, 학생/11).
    emotion = EmotionFrame(
        labels=list(_EMOTION_LABELS),
        points=[EmotionPoint(chapter_idx=c.idx, label=None, value=None) for c in chapters],
    )

    # 5) 편지 인물 선택지(학생/12): Bible characters 에서 id·name·traits 만.
    letter_characters = [
        LetterCharacter(
            id=c.get("id") or c.get("name", ""), name=c.get("name", ""), traits=c.get("traits", [])
        )
        for c in bible.get("characters", []) if c.get("name")
    ]

    return LearningResponse(
        vocab=vocab, quiz=quiz, essay_blanks=essay_blanks, emotion=emotion,
        letter_characters=letter_characters,
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
    bible = bible_rec.data if bible_rec else {}
    characters = bible.get("characters", []) if isinstance(bible.get("characters"), list) else []
    character = next((c for c in characters if isinstance(c, dict) and c.get("name") == to), None)
    if not character:
        raise validation_error("그 인물을 찾을 수 없어요.", {"field": "to"})

    # 이야기 배경·함께 겪은 일을 페르소나에 전달(결말 비공개). 본문 일부를 추억 맥락으로.
    story_context = _story_text(
        [c for c in store.list_chapters(book_id) if c.char_count > 0 and not getattr(c, "prefetched", False)]
    )[:1500]
    ap = character.get("appearance")
    appearance = ap if isinstance(ap, str) else (", ".join(str(v) for v in ap.values()) if isinstance(ap, dict) else None)
    reply = await chat.persona_reply(
        gemini, character.get("name", to), character.get("traits", []), body,
        species=character.get("species") or character.get("kind"),
        appearance=appearance,
        world=bible.get("world"),
        story_title=bible.get("title"),
        story_context=story_context or None,
    )
    letter = store.add_letter(
        book_id, user.id, to, body, status="answered", reply=reply, reply_source="ai"
    )
    store.add_learning_artifact(
        book_id, "letter", {"to": to, "body": body, "status": "answered", "replySaved": True}
    )
    return LetterResponse(status="answered", reply=reply, letter_id=letter.id)
