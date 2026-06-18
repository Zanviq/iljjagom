"""관리자 서비스 — 사용자·메시지·세션(enrich)·감사 로그. 추가기능 06.

모든 변경 행위는 audit_log 에 기록. require_role("admin") 은 라우터에서 강제.
"""
from __future__ import annotations

from typing import Any

from app.config import Settings
from app.deps import CurrentUser
from app.errors import conflict, not_found, validation_error
from app.models.schemas import (
    AdminMessage,
    AdminMessagesResponse,
    AdminSettingsResponse,
    AdminUser,
    AdminUserPatch,
    AdminUsersResponse,
    SettingPut,
    TokenUsageBucket,
    TokenUsageResponse,
)
from app.store.base import Store
from app.store.records import ProfileRecord

# app_settings 에 허용되는 비-시크릿 런타임 키(시크릿 저장 방지).
ALLOWED_SETTING_KEYS = {
    "models", "feature_toggles", "rate_limits", "notify_interval_sec", "safety_level",
}


def audit(store: Store, admin: CurrentUser, action: str, target: str | None, detail: dict) -> None:
    try:
        store.add_audit(admin.id, action, target, detail)
    except Exception:
        pass


def _user_class(store: Store, profile: ProfileRecord) -> tuple[str | None, str | None]:
    try:
        if profile.role == "teacher":
            rooms = store.list_classrooms_for_teacher(profile.id)
        else:
            rooms = store.list_classrooms_for_student(profile.id)
    except Exception:
        rooms = []
    if rooms:
        return rooms[0].id, rooms[0].name
    return None, None


def _to_admin_user(store: Store, p: ProfileRecord) -> AdminUser:
    class_id, class_name = _user_class(store, p)
    return AdminUser(
        id=p.id, email=p.email, role=p.role, class_id=class_id, class_name=class_name,
        grade=p.grade, guardian_consent=p.guardian_consent, status=p.status,
        created_at=p.created_at,
    )


def list_users(
    store: Store, query: str | None, role: str | None, class_id: str | None
) -> AdminUsersResponse:
    profiles = store.list_profiles(query=query, role=role)
    users = [_to_admin_user(store, p) for p in profiles]
    if class_id:
        users = [u for u in users if u.class_id == class_id]
    return AdminUsersResponse(users=users)


def patch_user(
    store: Store, admin: CurrentUser, target_id: str, patch: AdminUserPatch
) -> AdminUser:
    profile = store.get_profile(target_id)
    if not profile:
        raise not_found("사용자를 찾을 수 없습니다.")

    fields: dict[str, Any] = {}
    if patch.role is not None and patch.role != profile.role:
        # 마지막 관리자 강등 방지.
        if profile.role == "admin" and patch.role != "admin":
            if store.count_profiles_by_role("admin") <= 1:
                raise conflict("마지막 관리자는 강등할 수 없습니다.")
        fields["role"] = patch.role
    if patch.guardian_consent is not None:
        fields["guardian_consent"] = patch.guardian_consent

    if fields:
        store.update_profile_fields(target_id, **fields)

    # 학급 배정(학생) — 추가 등록(이동). 해제는 후속.
    if patch.class_id:
        try:
            store.enroll(patch.class_id, target_id)
        except Exception:
            pass

    audit(store, admin, "patch_user", target_id, {"fields": list(fields.keys()), "classId": patch.class_id})
    return _to_admin_user(store, store.get_profile(target_id))


def deactivate_user(store: Store, admin: CurrentUser, target_id: str) -> dict:
    profile = store.get_profile(target_id)
    if not profile:
        raise not_found("사용자를 찾을 수 없습니다.")
    if profile.role == "admin" and store.count_profiles_by_role("admin") <= 1:
        raise conflict("마지막 관리자는 비활성화할 수 없습니다.")
    store.update_profile_fields(target_id, status="deactivated")
    audit(store, admin, "deactivate_user", target_id, {})
    return {"id": target_id, "status": "deactivated"}


def list_messages(
    store: Store,
    user_id: str | None,
    book_id: str | None,
    kind: str | None,
    since: str | None,
    until: str | None,
    limit: int,
) -> AdminMessagesResponse:
    rows = store.list_messages_admin(
        user_id=user_id, book_id=book_id, kind=kind, since=since, until=until, limit=limit
    )
    return AdminMessagesResponse(
        messages=[
            AdminMessage(
                id=m.id, book_id=m.book_id, user_id=m.user_id, role=m.role, kind=m.kind,
                content=m.content, session_id=m.session_id, created_at=m.created_at,
            )
            for m in rows
        ]
    )


# --- settings (런타임 설정) ---
def get_settings_view(store: Store, settings: Settings) -> AdminSettingsResponse:
    return AdminSettingsResponse(
        settings=store.all_settings(),
        env={
            "googleApiKey": bool(settings.google_api_key),
            "supabaseUrl": bool(settings.supabase_url),
            "supabaseServiceRoleKey": bool(settings.supabase_service_role_key),
            "supabaseJwtSecret": bool(settings.supabase_jwt_secret),
        },
    )


def put_settings(
    store: Store, admin: CurrentUser, payload: SettingPut
) -> AdminSettingsResponse:
    updates: dict[str, Any] = {}
    if payload.settings is not None:
        updates.update(payload.settings)
    if payload.key is not None:
        updates[payload.key] = payload.value
    if not updates:
        raise validation_error("변경할 설정이 없습니다.")
    bad = [k for k in updates if k not in ALLOWED_SETTING_KEYS]
    if bad:
        raise validation_error(
            f"허용되지 않은 설정 키: {', '.join(bad)} (시크릿은 환경변수로만).",
            {"allowed": sorted(ALLOWED_SETTING_KEYS)},
        )
    for k, v in updates.items():
        store.set_setting(k, v, updated_by=admin.id)
    # 런타임 반영 — rate limit 설정 캐시 무효화.
    from app.ratelimit import reset as ratelimit_reset

    ratelimit_reset()
    audit(store, admin, "put_settings", None, {"keys": sorted(updates.keys())})
    from app.config import get_settings as _gs

    return get_settings_view(store, _gs())


# --- token usage ---
def token_usage(
    store: Store, group_by: str, since: str | None, until: str | None
) -> TokenUsageResponse:
    gb = group_by if group_by in ("model", "role", "day") else "model"
    agg = store.token_usage_buckets(group_by=gb, since=since, until=until)
    return TokenUsageResponse(
        group_by=gb,
        buckets=[TokenUsageBucket(**b) for b in agg["buckets"]],
        total=TokenUsageBucket(**agg["total"]),
    )
