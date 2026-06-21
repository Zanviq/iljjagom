"""중간활동 서비스 — 기·승 완료 후 필수 게이트(학생/15 §3).

기·승(free) 챕터가 모두 채워지면 중간 퀴즈/독후감을 풀어야 전·결(guided)로 진행할 수 있다.
그동안 전·결은 백그라운드 선생성(prefetch_arc)으로 미리 만들어진다. 콘텐츠는 13 키 규칙으로
`learning_artifacts(type="mid_activity")` 에 캐시한다.
"""
from __future__ import annotations

from app.ai import quiz as quizgen
from app.ai.gemini import GeminiClient
from app.ai.sanitize import sanitize_body
from app.errors import not_found
from app.models.schemas import EssayBlank, MidActivityResponse, QuizItem
from app.services import policy
from app.services.books import assert_can_access_book, assert_owner_student, get_book_or_404
from app.services.collab import COLLAB_TARGET_PARAGRAPHS
from app.services.learning import _source_sig
from app.store.base import Store

MID_ACTIVITY = "mid_activity"
MID_DONE_EVENT = "mid_activity_done"


def _resolve_bible(store: Store, book_id: str, bible: dict | None) -> dict:
    """bible(=BibleRecord.data) 가 주어지면 재조회 없이 그대로 쓴다(중복 조회 완화, 06 §7)."""
    if bible is not None:
        return bible
    rec = store.get_bible(book_id)
    return rec.data if rec else {}


def _free_events(store: Store, book_id: str, *, bible: dict | None = None) -> list[dict]:
    data = _resolve_bible(store, book_id, bible)
    return [e for e in data.get("events", []) if e.get("mode", "free") == "free"]


def _guided_events(store: Store, book_id: str, *, bible: dict | None = None) -> list[dict]:
    data = _resolve_bible(store, book_id, bible)
    return [e for e in data.get("events", []) if e.get("mode") == "guided"]


def _chapter_complete(store: Store, chapter, *, para_count: int | None = None) -> bool:
    """협업 챕터는 목표 문단 도달 시 완료. 비협업(SSE 통짜)은 본문 있으면 완료.

    para_count 를 넘기면 문단 재조회를 생략한다(N+1 완화, 06 §7).
    """
    pc = para_count if para_count is not None else len(store.list_paragraphs(chapter.id))
    if pc == 0:
        return chapter.char_count > 0
    return pc >= COLLAB_TARGET_PARAGRAPHS


def _giseung_chapters(store: Store, book_id: str, *, bible: dict | None = None, chapters=None) -> list:
    """기·승(free) 중 실제 본문이 있는 챕터(진입한 것)."""
    free_idx = {e.get("chapterIdx") for e in _free_events(store, book_id, bible=bible)}
    chs = chapters if chapters is not None else store.list_chapters(book_id)
    return [
        c for c in chs
        if c.idx in free_idx and c.char_count > 0 and not getattr(c, "prefetched", False)
    ]


def giseung_done(
    store: Store,
    book_id: str,
    *,
    bible: dict | None = None,
    chapters=None,
    para_counts: dict[str, int] | None = None,
) -> bool:
    """기·승 모든 free 챕터가 완료(협업 목표 문단 도달/본문 존재)면 True.

    bible/chapters/para_counts(chapter_id→문단수) 를 넘기면 재조회를 생략한다(N+1 완화, 06 §7).
    """
    data = _resolve_bible(store, book_id, bible)
    free = _free_events(store, book_id, bible=data)
    if not free:
        return False
    chs = chapters if chapters is not None else store.list_chapters(book_id)
    by_idx = {c.idx: c for c in chs}
    for e in free:
        c = by_idx.get(e.get("chapterIdx"))
        if not c:
            return False
        pc = para_counts.get(c.id) if para_counts is not None else None
        if not _chapter_complete(store, c, para_count=pc):
            return False
    return True


def is_done(store: Store, book_id: str) -> bool:
    try:
        return bool(store.list_events(book_id=book_id, type=MID_DONE_EVENT))
    except Exception:
        return False


def gate_blocked(
    store: Store,
    book_id: str,
    *,
    bible: dict | None = None,
    chapters=None,
    para_counts: dict[str, int] | None = None,
) -> bool:
    """전·결(guided) 진입 게이트 — 기·승 완료 + 전·결 존재 + 중간활동 미완료면 막는다.

    bible/chapters/para_counts 를 넘기면 재조회를 생략한다(bible 1회만 조회, 06 §7).
    """
    data = _resolve_bible(store, book_id, bible)
    return (
        giseung_done(store, book_id, bible=data, chapters=chapters, para_counts=para_counts)
        and bool(_guided_events(store, book_id, bible=data))
        and not is_done(store, book_id)
    )


async def get_mid_activity(
    store: Store, gemini: GeminiClient, user, book_id: str
) -> MidActivityResponse:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)

    # bible/chapters/문단수를 1회씩만 조회해 헬퍼들에 재사용(중복 조회 제거, 06 §7).
    bible_rec = store.get_bible(book_id)
    bible = bible_rec.data if bible_rec else {}
    chapters = store.list_chapters(book_id)
    para_counts: dict[str, int] = {}
    for p in store.list_paragraphs_for_book(book_id):
        para_counts[p.chapter_id] = para_counts.get(p.chapter_id, 0) + 1

    free_done = giseung_done(store, book_id, bible=bible, chapters=chapters, para_counts=para_counts)
    has_guided = bool(_guided_events(store, book_id, bible=bible))
    done = is_done(store, book_id)
    if not free_done or not has_guided:
        return MidActivityResponse(required=False, done=done)

    giseung = _giseung_chapters(store, book_id, bible=bible, chapters=chapters)
    sig = _source_sig(giseung)
    # 캐시 조회(13 키 규칙, type="mid_activity").
    for a in store.list_learning_artifacts(book_id=book_id, type=MID_ACTIVITY):
        if a.data.get("sourceSig") == sig:
            return MidActivityResponse(
                required=not done, done=done,
                quiz=[QuizItem(**q) for q in a.data.get("quiz", [])],
                essay_blanks=[EssayBlank(**e) for e in a.data.get("essayBlanks", [])],
            )

    # 미스 → 기·승 본문 내용 이해 + 학습목표를 학년 수준에 맞춰 실 퀴즈 생성(실패 시 템플릿).
    objectives = [e.get("objective") for e in _free_events(store, book_id, bible=bible) if e.get("objective")]
    story_text = "\n\n".join(
        f"[{c.idx}장]\n{sanitize_body(c.body).strip()}" for c in giseung if (c.body or "").strip()
    )
    grade = policy.resolve_grade(store, book=book)
    quiz = await quizgen.generate_quiz(
        gemini,
        story_text=story_text,
        objectives=[o for o in objectives if o],
        grade=grade,
        count=5,
        seed=f"{book_id}:mid",
    )
    essay = [EssayBlank(prompt="여기까지 이야기에서 가장 기억에 남는 장면은 무엇인가요?",
                        hints=["인물", "사건"])]
    try:
        store.add_learning_artifact(book_id, MID_ACTIVITY, {
            "sourceSig": sig,
            "quiz": [q.model_dump() for q in quiz],
            "essayBlanks": [e.model_dump() for e in essay],
        })
    except Exception:
        pass
    return MidActivityResponse(required=not done, done=done, quiz=quiz, essay_blanks=essay)


def complete_mid_activity(store: Store, user, book_id: str) -> MidActivityResponse:
    book = get_book_or_404(store, book_id)
    assert_owner_student(user, book) if user.role != "admin" else None
    if not giseung_done(store, book_id):
        raise not_found("아직 중간활동을 시작할 수 없어요(기·승 미완료).")
    if not is_done(store, book_id):
        store.add_events(user.id, [{"book_id": book_id, "type": MID_DONE_EVENT, "payload": {}}])
    return MidActivityResponse(required=False, done=True)
