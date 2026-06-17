"""인메모리 저장소 — 외부 키 없이 계약을 end-to-end 로 실행/테스트하기 위한 구현.

영속성은 없다(프로세스 메모리). 접근 제어(RLS 등가)는 서비스 계층이 담당한다.
"""
from __future__ import annotations

from typing import Any

from app.store.base import Store
from app.store.records import (
    AiSessionRecord,
    AiStepRecord,
    AuditRecord,
    BibleRecord,
    BookRecord,
    ChapterRecord,
    ChunkRecord,
    ClassroomRecord,
    MessageRecord,
    NotificationRecord,
    PlanMessageRecord,
    ProfileRecord,
    PromptRecord,
    SafetyFlagRecord,
    TokenUsageRecord,
)
from app.util import cosine_similarity, new_id, now_iso


class InMemoryStore(Store):
    def __init__(self) -> None:
        self.profiles: dict[str, ProfileRecord] = {}
        self.classrooms: dict[str, ClassroomRecord] = {}
        self.enrollments: set[tuple[str, str]] = set()
        self.prompts: dict[str, PromptRecord] = {}
        self.books: dict[str, BookRecord] = {}
        self.bibles: dict[str, BibleRecord] = {}
        self.chapters: dict[str, ChapterRecord] = {}
        self.plan_messages: list[PlanMessageRecord] = []
        self.chunks: list[ChunkRecord] = []
        self.safety_flags: list[SafetyFlagRecord] = []
        # 추가기능(03)
        self.ai_sessions: dict[str, AiSessionRecord] = {}
        self.ai_steps: list[AiStepRecord] = []
        self.messages: list[MessageRecord] = []
        self.token_usage: list[TokenUsageRecord] = []
        self.notifications: list[NotificationRecord] = []
        self.settings: dict[str, Any] = {}
        self.audit: list[AuditRecord] = []

    # --- profiles ---
    def get_profile(self, user_id: str) -> ProfileRecord | None:
        return self.profiles.get(user_id)

    def upsert_profile(self, profile: ProfileRecord) -> ProfileRecord:
        if not profile.created_at:
            profile.created_at = now_iso()
        self.profiles[profile.id] = profile
        return profile

    # --- classrooms / enrollments ---
    def create_classroom(
        self, teacher_id: str, name: str, code: str, school_id: str | None = None
    ) -> ClassroomRecord:
        rec = ClassroomRecord(
            id=new_id(),
            teacher_id=teacher_id,
            name=name,
            code=code,
            school_id=school_id,
            created_at=now_iso(),
        )
        self.classrooms[rec.id] = rec
        return rec

    def get_classroom(self, classroom_id: str) -> ClassroomRecord | None:
        return self.classrooms.get(classroom_id)

    def get_classroom_by_code(self, code: str) -> ClassroomRecord | None:
        for c in self.classrooms.values():
            if c.code.upper() == code.upper():
                return c
        return None

    def list_classrooms_for_teacher(self, teacher_id: str) -> list[ClassroomRecord]:
        return [c for c in self.classrooms.values() if c.teacher_id == teacher_id]

    def list_classrooms_for_student(self, student_id: str) -> list[ClassroomRecord]:
        ids = {cid for (cid, sid) in self.enrollments if sid == student_id}
        return [self.classrooms[cid] for cid in ids if cid in self.classrooms]

    def count_students(self, classroom_id: str) -> int:
        return sum(1 for (cid, _) in self.enrollments if cid == classroom_id)

    def list_student_ids(self, classroom_id: str) -> list[str]:
        return [sid for (cid, sid) in self.enrollments if cid == classroom_id]

    def enroll(self, classroom_id: str, student_id: str) -> None:
        self.enrollments.add((classroom_id, student_id))

    def is_enrolled(self, classroom_id: str, student_id: str) -> bool:
        return (classroom_id, student_id) in self.enrollments

    # --- prompts ---
    def create_prompt(
        self,
        classroom_id: str,
        topic: str,
        learning_objectives: list[str],
        assessment: dict[str, Any],
        language: str,
    ) -> PromptRecord:
        rec = PromptRecord(
            id=new_id(),
            classroom_id=classroom_id,
            topic=topic,
            learning_objectives=learning_objectives,
            assessment=assessment,
            language=language,
            created_at=now_iso(),
        )
        self.prompts[rec.id] = rec
        return rec

    def get_prompt(self, prompt_id: str) -> PromptRecord | None:
        return self.prompts.get(prompt_id)

    def list_prompts_for_class(self, classroom_id: str) -> list[PromptRecord]:
        return [p for p in self.prompts.values() if p.classroom_id == classroom_id]

    # --- books ---
    def create_book(
        self, student_id: str, classroom_id: str | None, prompt_id: str | None
    ) -> BookRecord:
        ts = now_iso()
        rec = BookRecord(
            id=new_id(),
            student_id=student_id,
            classroom_id=classroom_id,
            prompt_id=prompt_id,
            status="planning",
            created_at=ts,
            updated_at=ts,
        )
        self.books[rec.id] = rec
        return rec

    def get_book(self, book_id: str) -> BookRecord | None:
        return self.books.get(book_id)

    def update_book(self, book_id: str, **fields: Any) -> BookRecord:
        rec = self.books[book_id]
        for k, v in fields.items():
            setattr(rec, k, v)
        rec.updated_at = now_iso()  # 모든 변경은 마지막 활동 시각을 갱신한다.
        return rec

    def list_books_for_student(self, student_id: str) -> list[BookRecord]:
        return sorted(
            (b for b in self.books.values() if b.student_id == student_id),
            key=lambda b: b.updated_at or b.created_at,
            reverse=True,
        )

    def list_books_for_class(self, classroom_id: str) -> list[BookRecord]:
        return sorted(
            (b for b in self.books.values() if b.classroom_id == classroom_id),
            key=lambda b: b.updated_at or b.created_at,
            reverse=True,
        )

    # --- bibles ---
    def upsert_bible(self, book_id: str, data: dict[str, Any]) -> BibleRecord:
        rec = BibleRecord(book_id=book_id, data=data, created_at=now_iso())
        self.bibles[book_id] = rec
        return rec

    def get_bible(self, book_id: str) -> BibleRecord | None:
        return self.bibles.get(book_id)

    # --- chapters ---
    def create_chapter(self, book_id: str, idx: int, mode: str) -> ChapterRecord:
        rec = ChapterRecord(
            id=new_id(), book_id=book_id, idx=idx, mode=mode, created_at=now_iso()
        )
        self.chapters[rec.id] = rec
        return rec

    def get_chapter(self, book_id: str, idx: int) -> ChapterRecord | None:
        for c in self.chapters.values():
            if c.book_id == book_id and c.idx == idx:
                return c
        return None

    def list_chapters(self, book_id: str) -> list[ChapterRecord]:
        return sorted(
            (c for c in self.chapters.values() if c.book_id == book_id),
            key=lambda c: c.idx,
        )

    def update_chapter(self, chapter_id: str, **fields: Any) -> ChapterRecord:
        rec = self.chapters[chapter_id]
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    # --- plan messages ---
    def add_plan_message(self, book_id: str, role: str, content: str) -> PlanMessageRecord:
        rec = PlanMessageRecord(
            id=new_id(), book_id=book_id, role=role, content=content, created_at=now_iso()
        )
        self.plan_messages.append(rec)
        return rec

    def list_plan_messages(self, book_id: str) -> list[PlanMessageRecord]:
        return [m for m in self.plan_messages if m.book_id == book_id]

    # --- RAG chunks ---
    def add_chunk(
        self, book_id: str, chapter_id: str | None, content: str, embedding: list[float]
    ) -> ChunkRecord:
        rec = ChunkRecord(
            id=new_id(),
            book_id=book_id,
            chapter_id=chapter_id,
            content=content,
            embedding=embedding,
            created_at=now_iso(),
        )
        self.chunks.append(rec)
        return rec

    def search_chunks(
        self, book_id: str, query_embedding: list[float], k: int = 5
    ) -> list[ChunkRecord]:
        scored = [
            (cosine_similarity(query_embedding, c.embedding), c)
            for c in self.chunks
            if c.book_id == book_id
        ]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [c for _, c in scored[:k]]

    # --- safety ---
    def add_safety_flag(
        self, book_id: str | None, student_id: str | None, source: str, reason: str
    ) -> SafetyFlagRecord:
        rec = SafetyFlagRecord(
            id=new_id(),
            book_id=book_id,
            student_id=student_id,
            source=source,
            reason=reason,
            status="open",
            created_at=now_iso(),
        )
        self.safety_flags.append(rec)
        return rec

    # --- 관리자 집계 ---
    def usage_counts(self) -> dict[str, Any]:
        profiles = list(self.profiles.values())
        books = list(self.books.values())

        def role_n(r: str) -> int:
            return sum(1 for p in profiles if p.role == r)

        def status_n(s: str) -> int:
            return sum(1 for b in books if b.status == s)

        return {
            "users": {
                "total": len(profiles),
                "students": role_n("student"),
                "teachers": role_n("teacher"),
                "admins": role_n("admin"),
            },
            "classrooms": len(self.classrooms),
            "prompts": len(self.prompts),
            "books": {
                "total": len(books),
                "planning": status_n("planning"),
                "writing": status_n("writing"),
                "done": status_n("done"),
            },
            "chapters_written": sum(1 for c in self.chapters.values() if c.char_count > 0),
            "safety_flags": {
                "open": sum(1 for f in self.safety_flags if f.status == "open"),
                "total": len(self.safety_flags),
            },
        }

    # --- AI 세션 / ReAct 트레이스 ---
    def create_ai_session(
        self, book_id: str | None, role: str, model: str | None = None
    ) -> AiSessionRecord:
        rec = AiSessionRecord(
            id=new_id(), book_id=book_id, role=role, model=model,
            status="running", started_at=now_iso(),
        )
        self.ai_sessions[rec.id] = rec
        return rec

    def update_ai_session(self, session_id: str, **fields: Any) -> AiSessionRecord:
        rec = self.ai_sessions[session_id]
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    def get_ai_session(self, session_id: str) -> AiSessionRecord | None:
        return self.ai_sessions.get(session_id)

    def list_ai_sessions(
        self, book_id: str | None = None, status: str | None = None, limit: int = 50
    ) -> list[AiSessionRecord]:
        rows = [
            s for s in self.ai_sessions.values()
            if (book_id is None or s.book_id == book_id)
            and (status is None or s.status == status)
        ]
        rows.sort(key=lambda s: s.started_at, reverse=True)
        return rows[:limit]

    def add_ai_step(
        self, session_id: str, idx: int, thought: str | None, skill: str | None,
        args: dict[str, Any], observation: dict[str, Any],
        tokens_in: int = 0, tokens_out: int = 0, ms: int | None = None,
    ) -> AiStepRecord:
        rec = AiStepRecord(
            id=new_id(), session_id=session_id, idx=idx, thought=thought, skill=skill,
            args=args or {}, observation=observation or {},
            tokens_in=tokens_in, tokens_out=tokens_out, ms=ms, created_at=now_iso(),
        )
        self.ai_steps.append(rec)
        return rec

    def list_ai_steps(self, session_id: str) -> list[AiStepRecord]:
        return sorted(
            (s for s in self.ai_steps if s.session_id == session_id),
            key=lambda s: s.idx,
        )

    # --- messages ---
    def add_message(
        self, book_id: str | None, user_id: str | None, role: str, kind: str,
        content: str, session_id: str | None = None,
    ) -> MessageRecord:
        rec = MessageRecord(
            id=new_id(), book_id=book_id, user_id=user_id, role=role, kind=kind,
            content=content, session_id=session_id, created_at=now_iso(),
        )
        self.messages.append(rec)
        return rec

    def list_messages(self, book_id: str, kind: str | None = None) -> list[MessageRecord]:
        return sorted(
            (m for m in self.messages
             if m.book_id == book_id and (kind is None or m.kind == kind)),
            key=lambda m: m.created_at,
        )

    # --- token_usage ---
    def add_token_usage(
        self, session_id: str | None, model: str,
        tokens_in: int = 0, tokens_out: int = 0, est_cost: float = 0.0,
    ) -> TokenUsageRecord:
        rec = TokenUsageRecord(
            id=new_id(), session_id=session_id, model=model,
            tokens_in=tokens_in, tokens_out=tokens_out, est_cost=est_cost,
            created_at=now_iso(),
        )
        self.token_usage.append(rec)
        return rec

    def token_usage_summary(self, since: str | None = None) -> dict[str, Any]:
        rows = [u for u in self.token_usage if since is None or u.created_at >= since]
        by_model: dict[str, dict[str, Any]] = {}
        for u in rows:
            m = by_model.setdefault(
                u.model, {"calls": 0, "tokens_in": 0, "tokens_out": 0, "est_cost": 0.0}
            )
            m["calls"] += 1
            m["tokens_in"] += u.tokens_in
            m["tokens_out"] += u.tokens_out
            m["est_cost"] += u.est_cost
        return {
            "calls": len(rows),
            "tokens_in": sum(u.tokens_in for u in rows),
            "tokens_out": sum(u.tokens_out for u in rows),
            "est_cost": sum(u.est_cost for u in rows),
            "by_model": by_model,
        }

    # --- notifications ---
    def create_notification(
        self, title: str, body: str | None = None, level: str = "info",
        target_user_id: str | None = None, target_role: str | None = None,
        is_broadcast: bool = False,
    ) -> NotificationRecord:
        rec = NotificationRecord(
            id=new_id(), target_user_id=target_user_id, target_role=target_role,
            is_broadcast=is_broadcast, title=title, body=body, level=level,
            created_at=now_iso(),
        )
        self.notifications.append(rec)
        return rec

    def list_notifications(
        self, user_id: str, role: str, unread_only: bool = False, limit: int = 50
    ) -> list[NotificationRecord]:
        def visible(n: NotificationRecord) -> bool:
            if n.target_user_id == user_id or n.is_broadcast:
                return True
            return n.target_role is not None and n.target_role == role

        rows = [
            n for n in self.notifications
            if visible(n) and (not unread_only or n.read_at is None)
        ]
        rows.sort(key=lambda n: n.created_at, reverse=True)
        return rows[:limit]

    def mark_notification_read(self, notification_id: str, user_id: str) -> None:
        for n in self.notifications:
            if n.id == notification_id and (
                n.target_user_id == user_id or n.is_broadcast or n.target_role
            ):
                if n.read_at is None:
                    n.read_at = now_iso()
                return

    # --- app_settings ---
    def get_setting(self, key: str) -> Any | None:
        return self.settings.get(key)

    def set_setting(self, key: str, value: Any, updated_by: str | None = None) -> None:
        self.settings[key] = value

    def all_settings(self) -> dict[str, Any]:
        return dict(self.settings)

    # --- audit_log ---
    def add_audit(
        self, admin_id: str | None, action: str, target: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> AuditRecord:
        rec = AuditRecord(
            id=new_id(), admin_id=admin_id, action=action, target=target,
            detail=detail or {}, created_at=now_iso(),
        )
        self.audit.append(rec)
        return rec

    def list_audit(self, limit: int = 100) -> list[AuditRecord]:
        return sorted(self.audit, key=lambda a: a.created_at, reverse=True)[:limit]
