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
    AiSessionView,
    BackupExportResponse,
    BackupImportResponse,
    BookTimeline,
    BookTimelineChapter,
    LearningResult,
    MessagesByUser,
    MessagesByUserRow,
    Notification,
    NotificationCreate,
    NotificationsResponse,
    PlanMessageView,
    SettingPut,
    TokenUsageBucket,
    TokenUsageResponse,
    UserOverview,
    UserOverviewBook,
)
from app.store.base import Store
from app.store.records import AiSessionRecord, NotificationRecord, ProfileRecord
from app.util import now_iso

# role → 단계 라벨(관리자/01 §5).
_STAGE_LABEL = {
    "designer": "설계(Bible)", "writer": "집필", "editor": "편집(수정)",
    "chat": "학습 대화", "tutor": "학습 대화", "overseer": "총괄(곰 작가)", "letter": "편지 검수",
}


def _session_brief(store: Store, s: AiSessionRecord) -> AiSessionView:
    """드릴다운용 세션 요약(스텝 합산 없이 가볍게). 단계 라벨·책 맥락 포함."""
    view = AiSessionView(
        id=s.id, book_id=s.book_id, role=s.role, model=s.model, status=s.status,
        summary=s.summary, error=s.error, started_at=s.started_at, ended_at=s.ended_at,
        stage=_STAGE_LABEL.get(s.role or "", s.role),
    )
    if s.book_id:
        b = store.get_book(s.book_id)
        if b:
            view.book_title = b.title
            view.book_status = b.status
    return view

# app_settings 에 허용되는 비-시크릿 런타임 키(시크릿 저장 방지).
ALLOWED_SETTING_KEYS = {
    "models", "feature_toggles", "rate_limits", "notify_interval_sec", "safety_level",
}

# 설정 키별 enum/타입 스키마 — 콘솔이 raw JSON 대신 Select/Switch/Stepper 로 렌더(관리자/02).
SETTINGS_SCHEMA: dict[str, Any] = {
    "safety_level": {"type": "enum", "options": ["relaxed", "standard", "strict"],
                     "default": "standard"},
    "notify_interval_sec": {"type": "int", "min": 30, "max": 3600, "default": 180},
    "feature_toggles": {"type": "object", "valueType": "boolean"},
    "models": {"type": "object",
               "roles": ["designer", "writer", "editor", "chat", "embed", "imagen"]},
    "rate_limits": {"type": "object", "valueType": "number"},
}


def settings_schema() -> dict[str, Any]:
    return {"schema": SETTINGS_SCHEMA}

# 백업 대상 화이트리스트(임베딩·rate 카운터 제외).
ALLOWED_BACKUP_TABLES = [
    "profiles", "schools", "classrooms", "enrollments", "prompts", "books", "bibles",
    "chapters", "plan_messages", "learning_artifacts", "events", "safety_flags", "letters",
    "ai_sessions", "ai_steps", "messages", "token_usage", "notifications", "app_settings",
    "audit_log",
]


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
    emails = _email_cache(store, {m.user_id for m in rows if m.user_id})
    return AdminMessagesResponse(
        messages=[
            AdminMessage(
                id=m.id, book_id=m.book_id, user_id=m.user_id, user_email=emails.get(m.user_id),
                role=m.role, kind=m.kind, content=m.content, session_id=m.session_id,
                created_at=m.created_at,
            )
            for m in rows
        ]
    )


def _email_cache(store: Store, user_ids: set[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for uid in user_ids:
        prof = store.get_profile(uid)
        out[uid] = prof.email if prof else None
    return out


def list_messages_by_user(store: Store, limit: int = 1000) -> MessagesByUser:
    """대화 페이지 '사용자 목록' — user 단위 집계(관리자/01)."""
    rows = store.list_messages_admin(limit=limit)
    agg: dict[str, dict] = {}
    for m in rows:
        if not m.user_id:
            continue
        a = agg.setdefault(m.user_id, {"count": 0, "books": set(), "last": ""})
        a["count"] += 1
        if m.book_id:
            a["books"].add(m.book_id)
        if (m.created_at or "") > a["last"]:
            a["last"] = m.created_at or ""
    users = []
    for uid, a in agg.items():
        prof = store.get_profile(uid)
        users.append(MessagesByUserRow(
            user_id=uid, email=prof.email if prof else None,
            role=prof.role if prof else None,
            message_count=a["count"], book_count=len(a["books"]), last_at=a["last"] or None,
        ))
    users.sort(key=lambda u: u.last_at or "", reverse=True)
    return MessagesByUser(users=users)


def user_overview(store: Store, admin: CurrentUser, user_id: str) -> UserOverview:
    """한 사용자의 책·세션·최근 대화 요약(관리자/01)."""
    prof = store.get_profile(user_id)
    if not prof:
        raise not_found("사용자를 찾을 수 없습니다.")
    audit(store, admin, "view_user_overview", user_id, {})

    books = []
    sessions: list[AiSessionView] = []
    for b in store.list_books_for_student(user_id):
        bsessions = store.list_ai_sessions(book_id=b.id, limit=50)
        bmsgs = store.list_messages_admin(book_id=b.id, limit=500)
        books.append(UserOverviewBook(
            id=b.id, title=b.title, status=b.status, created_at=b.created_at,
            session_count=len(bsessions), message_count=len(bmsgs),
        ))
        sessions.extend(_session_brief(store, s) for s in bsessions)
    recent = store.list_messages_admin(user_id=user_id, limit=20)
    emails = _email_cache(store, {user_id})
    return UserOverview(
        user=_to_admin_user(store, prof),
        books=books,
        sessions=sessions,
        recent_messages=[
            AdminMessage(
                id=m.id, book_id=m.book_id, user_id=m.user_id, user_email=emails.get(m.user_id),
                role=m.role, kind=m.kind, content=m.content, session_id=m.session_id,
                created_at=m.created_at,
            )
            for m in recent
        ],
    )


def book_timeline(store: Store, admin: CurrentUser, book_id: str) -> BookTimeline:
    """한 책의 단계별 통합 타임라인(관리자/01)."""
    from app.services.books import _to_book
    from app.services.teacher import _to_prompt

    book = store.get_book(book_id)
    if not book:
        raise not_found("책을 찾을 수 없습니다.")
    audit(store, admin, "view_book_timeline", book_id, {})

    prompt = store.get_prompt(book.prompt_id) if book.prompt_id else None
    chapters = [
        BookTimelineChapter(idx=c.idx, review_status=c.review_status, char_count=c.char_count)
        for c in store.list_chapters(book_id)
    ]
    sessions = [_session_brief(store, s) for s in store.list_ai_sessions(book_id=book_id, limit=100)]
    plan_msgs = [
        PlanMessageView(role=m.role, content=m.content, created_at=m.created_at)
        for m in store.list_plan_messages(book_id)
    ]
    emails = _email_cache(store, {book.student_id} if book.student_id else set())
    messages = [
        AdminMessage(
            id=m.id, book_id=m.book_id, user_id=m.user_id, user_email=emails.get(m.user_id),
            role=m.role, kind=m.kind, content=m.content, session_id=m.session_id,
            created_at=m.created_at,
        )
        for m in store.list_messages_admin(book_id=book_id, limit=500)
    ]
    learning = [
        LearningResult(id=a.id, type=a.type, data=a.data, created_at=a.created_at)
        for a in store.list_learning_artifacts(book_id=book_id) if a.type != "learning_set"
    ]
    return BookTimeline(
        book=_to_book(book), prompt=_to_prompt(prompt) if prompt else None,
        chapters=chapters, sessions=sessions, plan_messages=plan_msgs,
        messages=messages, learning=learning,
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
    # enum 검증(관리자/02): safety_level 은 정의된 값만.
    if "safety_level" in updates and updates["safety_level"] not in SETTINGS_SCHEMA["safety_level"]["options"]:
        raise validation_error("안전강도 값이 올바르지 않아요.",
                               {"options": SETTINGS_SCHEMA["safety_level"]["options"]})
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


# --- notifications ---
def _notif_view(n: NotificationRecord) -> Notification:
    return Notification(
        id=n.id, target_user_id=n.target_user_id, target_role=n.target_role,
        is_broadcast=n.is_broadcast, title=n.title, body=n.body, level=n.level,
        read_at=n.read_at, created_at=n.created_at,
    )


def list_notifications(
    store: Store, user: CurrentUser, unread: bool, limit: int
) -> NotificationsResponse:
    rows = store.list_notifications(user.id, user.role, unread_only=unread, limit=limit)
    return NotificationsResponse(notifications=[_notif_view(n) for n in rows])


def create_notification(
    store: Store, admin: CurrentUser, payload: NotificationCreate
) -> Notification:
    rec = store.create_notification(
        title=payload.title, body=payload.body, level=payload.level,
        target_user_id=payload.target_user_id, target_role=payload.target_role,
        is_broadcast=payload.is_broadcast,
    )
    audit(store, admin, "send_notification", rec.id,
          {"target": payload.target_user_id or payload.target_role or "broadcast"})
    return _notif_view(rec)


def mark_notification_read(store: Store, user: CurrentUser, notif_id: str) -> dict:
    store.mark_notification_read(notif_id, user.id)
    return {"id": notif_id, "readAt": now_iso()}


# --- backup ---
def export_backup(store: Store, admin: CurrentUser, tables: list[str] | None) -> BackupExportResponse:
    targets = [t for t in (tables or ALLOWED_BACKUP_TABLES) if t in ALLOWED_BACKUP_TABLES]
    data = store.export_tables(targets)
    audit(store, admin, "backup_export", None, {"tables": targets})
    return BackupExportResponse(exported_at=now_iso(), tables=data)


def import_backup(
    store: Store, admin: CurrentUser, mode: str, tables: dict
) -> BackupImportResponse:
    safe = {t: rows for t, rows in (tables or {}).items() if t in ALLOWED_BACKUP_TABLES}
    counts = store.import_tables(mode, safe)
    audit(store, admin, "backup_import", None, {"mode": mode, "tables": list(safe.keys())})
    return BackupImportResponse(imported=counts)


# --- 백그라운드 자동 알림(06 §3.8) ---
def run_notify_cycle(store: Store) -> int:
    """새 안전신호/오류 세션을 감지해 관리자 알림 생성. 마지막 점검 시각으로 dedup."""
    last = store.get_setting("_notify_last_check")
    created = 0
    try:
        open_flags = store.list_safety_flags(status="open", limit=500)
        new_flags = [f for f in open_flags if last is None or (f.created_at or "") > last]
        if new_flags:
            store.create_notification(
                title=f"미처리 안전 신호 {len(new_flags)}건",
                body="검토가 필요한 안전 신호가 있습니다.", level="warn", target_role="admin",
            )
            created += 1
        err_sessions = store.list_ai_sessions(status="error", limit=500)
        new_err = [s for s in err_sessions if last is None or (s.started_at or "") > last]
        if new_err:
            store.create_notification(
                title=f"오류 세션 {len(new_err)}건",
                body="실패한 AI 세션이 있습니다.", level="error", target_role="admin",
            )
            created += 1
    except Exception:
        pass
    store.set_setting("_notify_last_check", now_iso())
    return created
