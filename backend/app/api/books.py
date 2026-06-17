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
from app.models.schemas import CreateBookRequest, LetterRequest, serialize
from app.ratelimit import rate_limit
from app.services import books, learning, words
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
