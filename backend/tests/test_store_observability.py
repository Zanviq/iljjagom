"""신규 Store 메서드 계약 테스트 — AI 세션/트레이스/대화/토큰/알림/설정/감사.

InMemoryStore 로 계약을 검증한다(SupabaseStore 는 동일 시그니처를 구현).
"""
from __future__ import annotations

from app.store.memory import InMemoryStore


def _store() -> InMemoryStore:
    return InMemoryStore()


def test_ai_session_lifecycle_and_steps():
    s = _store()
    sess = s.create_ai_session(book_id="b1", role="designer", model="gemini-2.5-pro")
    assert sess.status == "running"
    assert s.get_ai_session(sess.id).id == sess.id

    s.add_ai_step(sess.id, 0, "생각1", "generate_text", {"a": 1}, {"ok": True}, 100, 50, 1200)
    s.add_ai_step(sess.id, 1, "생각2", "update_bible", {}, {"ok": True}, 10, 5, 300)
    steps = s.list_ai_steps(sess.id)
    assert [st.idx for st in steps] == [0, 1]
    assert steps[0].skill == "generate_text"

    s.update_ai_session(sess.id, status="done", summary="완료")
    assert s.get_ai_session(sess.id).status == "done"

    running = s.list_ai_sessions(status="running")
    assert sess.id not in [r.id for r in running]
    by_book = s.list_ai_sessions(book_id="b1")
    assert by_book[0].id == sess.id


def test_messages_unified():
    s = _store()
    s.add_message("b1", "u1", "user", "plan", "안녕")
    s.add_message("b1", None, "ai", "plan", "반가워")
    s.add_message("b1", "u1", "user", "letter", "편지")
    plan = s.list_messages("b1", kind="plan")
    assert len(plan) == 2
    assert s.list_messages("b1")[0].content == "안녕"


def test_token_usage_summary():
    s = _store()
    s.add_token_usage("sess1", "gemini-2.5-flash", 100, 200, 0.001)
    s.add_token_usage("sess1", "gemini-2.5-flash", 50, 60, 0.0005)
    s.add_token_usage("sess2", "gemini-2.5-pro", 1000, 300, 0.01)
    summary = s.token_usage_summary()
    assert summary["calls"] == 3
    assert summary["tokens_in"] == 1150
    assert summary["by_model"]["gemini-2.5-flash"]["calls"] == 2
    assert abs(summary["est_cost"] - 0.0115) < 1e-9


def test_notifications_targeting_and_read():
    s = _store()
    s.create_notification("개인", target_user_id="u1")
    s.create_notification("교사알림", target_role="teacher")
    s.create_notification("전체", is_broadcast=True)

    u1_student = s.list_notifications("u1", "student")
    titles = {n.title for n in u1_student}
    assert titles == {"개인", "전체"}  # 역할(teacher) 알림은 안 보임

    teacher = s.list_notifications("u2", "teacher")
    assert {n.title for n in teacher} == {"교사알림", "전체"}

    target = u1_student[0]
    s.mark_notification_read(target.id, "u1")
    unread = s.list_notifications("u1", "student", unread_only=True)
    assert target.id not in [n.id for n in unread]


def test_app_settings_roundtrip():
    s = _store()
    s.set_setting("notify_interval_sec", 180)
    s.set_setting("models", {"writer": "gemini-2.5-flash"})
    assert s.get_setting("notify_interval_sec") == 180
    assert s.get_setting("models")["writer"] == "gemini-2.5-flash"
    assert s.get_setting("missing") is None
    assert "models" in s.all_settings()


def test_audit_log():
    s = _store()
    s.add_audit("admin1", "set_setting", "models", {"key": "models"})
    s.add_audit("admin1", "send_notification", None, {})
    rows = s.list_audit()
    assert len(rows) == 2
    assert rows[0].action in {"set_setting", "send_notification"}


def test_rate_hit_counts_within_window():
    s = _store()
    # 같은 (bucket, user) 호출은 윈도 내 누적 카운트를 반환한다.
    assert s.rate_hit("design", "u1", 60) == 1
    assert s.rate_hit("design", "u1", 60) == 2
    assert s.rate_hit("design", "u1", 60) == 3
    # 다른 사용자/버킷은 독립.
    assert s.rate_hit("design", "u2", 60) == 1
    assert s.rate_hit("revise", "u1", 60) == 1
    # window 음수면 직전 기록이 항상 만료되어 카운트 1 유지.
    assert s.rate_hit("design", "u3", -1) == 1
    assert s.rate_hit("design", "u3", -1) == 1
