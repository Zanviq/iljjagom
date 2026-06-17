"""책 라우터 — 생성/조회/단어도움."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.ai.gemini import GeminiClient, get_gemini
from app.deps import CurrentUser, get_current_user, get_store_dep, require_role
from app.models.schemas import CreateBookRequest, serialize
from app.services import books, words
from app.store.base import Store

router = APIRouter(tags=["books"])


@router.post("/books", status_code=201)
async def create_book(
    req: CreateBookRequest,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
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
