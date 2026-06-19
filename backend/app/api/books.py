"""책 라우터 — 생성/조회/단어도움."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.ai.gemini import GeminiClient, get_gemini
from app.deps import (
    CurrentUser,
    get_current_user,
    get_store_dep,
    require_guardian_consent,
    require_role,
)
from app.models.schemas import (
    CreateBookRequest,
    LearningResultCreate,
    LetterRequest,
    serialize,
)
from app.ratelimit import rate_limit
from app.services import books, events, learning, words
from app.services import safety as safety_service
from app.store.base import Store

router = APIRouter(tags=["books"])


@router.post("/books", status_code=201)
async def create_book(
    req: CreateBookRequest,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    _consent: CurrentUser = Depends(require_guardian_consent()),
) -> dict:
    book = books.create_book(store, user, req.prompt_id)
    return serialize(book)


@router.get("/books")
async def list_books(
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    # 학생 "내 책/이어 읽기" 목록. 최근 활동 순.
    return serialize(books.list_books(store, user))


@router.get("/books/{book_id}")
async def get_book(
    book_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    detail = books.get_book_detail(store, user, book_id)
    return serialize(detail)


# --- 학생 데이터 열람 (선생님/03, 책 접근자: 소유 학생·담당 교사·admin) ---
@router.get("/books/{book_id}/chapters")
async def list_chapters_content(
    book_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(books.list_chapters_content(store, user, book_id))


@router.get("/books/{book_id}/chapters/{idx}/content")
async def get_chapter_content(
    book_id: str,
    idx: int,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(books.get_chapter_content(store, user, book_id, idx))


@router.get("/books/{book_id}/plan-messages")
async def get_plan_messages(
    book_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(books.get_plan_messages(store, user, book_id))


@router.get("/books/{book_id}/bible")
async def get_bible(
    book_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(books.get_bible_view(store, user, book_id))


@router.get("/books/{book_id}/words")
async def get_word(
    book_id: str,
    term: str = Query(min_length=1),
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
) -> dict:
    # 책 접근 권한 확인 후 단어 조회.
    book = books.get_book_or_404(store, book_id)
    books.assert_can_access_book(store, user, book)
    word = await words.lookup(gemini, term)
    return serialize(word)


@router.get("/books/{book_id}/learning")
async def get_learning(
    book_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
    _rl: None = Depends(rate_limit("learning", 30)),
) -> dict:
    # 어휘/퀴즈/독후감/감정 곡선 (FR-S8~S12). 책 접근 가능자.
    result = await learning.build_learning(store, gemini, user, book_id)
    return serialize(result)


@router.post("/books/{book_id}/learning-results", status_code=201)
async def post_learning_result(
    book_id: str,
    req: LearningResultCreate,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    _rl: None = Depends(rate_limit("learning-results", 30)),
) -> dict:
    # 퀴즈/독후감/감정 자기보고 저장(learning_artifacts). essay는 안전 게이트 통과.
    created = events.save_learning_result(store, user, book_id, req.type, req.data)
    return serialize(created)


@router.get("/books/{book_id}/learning-results")
async def get_learning_results(
    book_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    # 책 접근 가능자(학생 본인·교사·admin)가 학습 결과 조회.
    return serialize(events.list_learning_results(store, user, book_id))


@router.get("/books/{book_id}/letters")
async def list_book_letters(
    book_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    # 학생이 자기 편지 상태(보류/승인된 답장)를 확인. 책 접근 가능자.
    return serialize(safety_service.list_book_letters(store, user, book_id))


@router.post("/books/{book_id}/letters")
async def post_letter(
    book_id: str,
    req: LetterRequest,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    gemini: GeminiClient = Depends(get_gemini),
    _rl: None = Depends(rate_limit("letters", 20)),
    _consent: CurrentUser = Depends(require_guardian_consent()),
) -> dict:
    # 인물에게 편지 → 페르소나 답장(정서 위험 시 보류). FR-S11.
    result = await learning.write_letter(store, gemini, user, book_id, req.to, req.body)
    return serialize(result)
