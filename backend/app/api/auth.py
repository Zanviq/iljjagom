"""인증/계정 라우터 — GET /me, POST /onboarding."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user, get_store_dep
from app.models.schemas import Me, OnboardingRequest, serialize
from app.services import accounts
from app.store.base import Store

router = APIRouter(tags=["auth"])


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)) -> dict:
    return serialize(accounts.build_me(user))


@router.post("/onboarding")
async def onboarding(
    req: OnboardingRequest,
    user: CurrentUser = Depends(get_current_user),
    store: Store = Depends(get_store_dep),
) -> dict:
    result: Me = accounts.onboard(store, user, req)
    return serialize(result)
