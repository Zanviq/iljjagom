"""교사 라우터 — 학급 목록, 발제 생성/조회."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user, get_store_dep, require_role
from app.models.schemas import (
    ClassesResponse,
    CreatePromptRequest,
    DashboardResponse,
    PromptsResponse,
    serialize,
)
from app.services import teacher
from app.store.base import Store

router = APIRouter(tags=["teacher"])


@router.get("/classes")
async def list_classes(
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    classes = teacher.list_classes(store, user)
    return serialize(ClassesResponse(classes=classes))


@router.post("/classes/{class_id}/prompts", status_code=201)
async def create_prompt(
    class_id: str,
    req: CreatePromptRequest,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    prompt = teacher.create_prompt(store, user, class_id, req)
    return serialize(prompt)


@router.get("/classes/{class_id}/dashboard")
async def class_dashboard(
    class_id: str,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.class_dashboard(store, user, class_id))


@router.get("/classes/{class_id}/prompts")
async def list_prompts(
    class_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    prompts = teacher.list_prompts(store, user, class_id)
    return serialize(PromptsResponse(prompts=prompts))
