"""교사 라우터 — 학급 목록, 발제 생성/조회."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.deps import CurrentUser, get_current_user, get_store_dep, require_role
from app.models.schemas import (
    ClassesResponse,
    ClassSettingsPut,
    CreateClassRequest,
    CreatePromptRequest,
    PromptsResponse,
    UpdateClassRequest,
    UpdatePromptRequest,
    serialize,
)
from app.ratelimit import rate_limit
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


@router.post("/classes", status_code=201)
async def create_class(
    req: CreateClassRequest,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.create_class(store, user, req.name))


@router.patch("/classes/{class_id}")
async def update_class(
    class_id: str,
    req: UpdateClassRequest,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.rename_class(store, user, class_id, req.name))


@router.post("/classes/{class_id}/rotate-code")
async def rotate_code(
    class_id: str,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
    _rl: None = Depends(rate_limit("rotate-code", 10)),
) -> dict:
    return serialize(teacher.rotate_class_code(store, user, class_id))


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
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.class_dashboard(store, user, class_id, from_, to))


@router.get("/classes/{class_id}/dashboard/history")
async def class_dashboard_history(
    class_id: str,
    group_by: str = Query(default="week", alias="groupBy"),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.class_dashboard_history(store, user, class_id, group_by, from_, to))


@router.get("/classes/{class_id}/settings")
async def get_class_settings(
    class_id: str,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.get_class_settings(store, user, class_id))


@router.put("/classes/{class_id}/settings")
async def put_class_settings(
    class_id: str,
    req: ClassSettingsPut,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.put_class_settings(store, user, class_id, req))


@router.patch("/classes/{class_id}/prompts/{prompt_id}")
async def update_prompt(
    class_id: str,
    prompt_id: str,
    req: UpdatePromptRequest,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.update_prompt(store, user, class_id, prompt_id, req))


@router.post("/classes/{class_id}/prompts/{prompt_id}/close")
async def close_prompt(
    class_id: str,
    prompt_id: str,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.close_prompt(store, user, class_id, prompt_id))


@router.get("/classes/{class_id}/prompts")
async def list_prompts(
    class_id: str,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    prompts = teacher.list_prompts(store, user, class_id)
    return serialize(PromptsResponse(prompts=prompts))


@router.get("/classes/{class_id}/prompts/{prompt_id}/submissions")
async def prompt_submissions(
    class_id: str,
    prompt_id: str,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    return serialize(teacher.prompt_submissions(store, user, class_id, prompt_id))


@router.get("/classes/{class_id}/students/{student_id}/books")
async def student_books(
    class_id: str,
    student_id: str,
    user: CurrentUser = Depends(require_role("teacher", "admin")),
    store: Store = Depends(get_store_dep),
) -> dict:
    from app.services import books

    return serialize(books.list_student_books(store, user, class_id, student_id))
