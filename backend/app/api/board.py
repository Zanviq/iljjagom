"""학급 게시판 라우터 — 발표 등록/목록/상세/승인/반려(학생/15 §4 · 14)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.deps import (
    CurrentUser,
    get_current_user,
    get_store_dep,
    require_guardian_consent,
    require_role,
)
from app.models.schemas import BoardPostCreate, BoardRejectRequest, serialize
from app.ratelimit import rate_limit
from app.services import board
from app.store.base import Store

router = APIRouter(tags=["board"])


@router.post("/books/{book_id}/board-posts")
async def create_board_post(
    book_id: str,
    req: BoardPostCreate,
    user: CurrentUser = Depends(require_role("student", "admin")),
    store: Store = Depends(get_store_dep),
    _rl: None = Depends(rate_limit("board", 30)),
    _consent: CurrentUser = Depends(require_guardian_consent()),
) -> dict:
    return serialize(board.create_board_post(store, user, book_id, req.intro))


@router.get("/classes/{class_id}/board-posts")
async def list_board_posts(
    class_id: str,
    status: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(board.list_board_posts(store, user, class_id, status))


@router.get("/board-posts/{post_id}")
async def get_board_post(
    post_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(board.get_board_post(store, user, post_id))


@router.post("/board-posts/{post_id}/approve")
async def approve_board_post(
    post_id: str,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(board.approve_board_post(store, user, post_id))


@router.post("/board-posts/{post_id}/reject")
async def reject_board_post(
    post_id: str,
    req: BoardRejectRequest,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(board.reject_board_post(store, user, post_id, req.note))
