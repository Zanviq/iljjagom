"""Supabase 저장소 — 서비스 롤 클라이언트(워커/서버)로 테이블에 접근한다.

서비스 롤은 RLS를 우회하므로, 접근 제어는 0002_rls.sql(유저 토큰 경로)와
서비스 계층의 권한 검사로 이중 보장한다. 본 클래스는 영속화만 담당.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import Settings
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
    EventRecord,
    LearningArtifactRecord,
    LetterRecord,
    MessageRecord,
    NotificationRecord,
    PlanMessageRecord,
    ProfileRecord,
    PromptRecord,
    SafetyFlagRecord,
    TokenUsageRecord,
)
from app.util import cosine_similarity, now_iso

# PostgREST 필터 보간 전 검증용 — UUID 형식 / 허용 역할.
_UUID_RE = re.compile(r"\A[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z")
_VALID_ROLES = {"student", "teacher", "admin"}


class SupabaseStore(Store):
    def __init__(self, settings: Settings) -> None:
        from supabase import create_client

        self.client = create_client(
            settings.supabase_url, settings.supabase_service_role_key
        )

    def _rows(self, resp: Any) -> list[dict]:
        return resp.data or []

    def _one(self, resp: Any) -> dict | None:
        rows = self._rows(resp)
        return rows[0] if rows else None

    # --- profiles ---
    def get_profile(self, user_id: str) -> ProfileRecord | None:
        row = self._one(
            self.client.table("profiles").select("*").eq("id", user_id).limit(1).execute()
        )
        return ProfileRecord(**row) if row else None

    def upsert_profile(self, profile: ProfileRecord) -> ProfileRecord:
        payload = {
            "id": profile.id,
            "email": profile.email,
            "role": profile.role,
            "guardian_consent": profile.guardian_consent,
            "grade": profile.grade,
        }
        row = self._one(self.client.table("profiles").upsert(payload).execute())
        return ProfileRecord(**row) if row else profile

    # --- classrooms / enrollments ---
    def create_classroom(
        self, teacher_id: str, name: str, code: str, school_id: str | None = None
    ) -> ClassroomRecord:
        row = self._one(
            self.client.table("classrooms")
            .insert(
                {"teacher_id": teacher_id, "name": name, "code": code, "school_id": school_id}
            )
            .execute()
        )
        return ClassroomRecord(**row)

    def get_classroom(self, classroom_id: str) -> ClassroomRecord | None:
        row = self._one(
            self.client.table("classrooms").select("*").eq("id", classroom_id).limit(1).execute()
        )
        return ClassroomRecord(**row) if row else None

    def get_classroom_by_code(self, code: str) -> ClassroomRecord | None:
        # 리터럴 매칭(.eq). ilike 는 %/_ 가 와일드카드로 해석돼 패턴 주입 위험이 있다.
        row = self._one(
            self.client.table("classrooms").select("*").eq("code", code.upper()).limit(1).execute()
        )
        return ClassroomRecord(**row) if row else None

    def list_classrooms_for_teacher(self, teacher_id: str) -> list[ClassroomRecord]:
        rows = self._rows(
            self.client.table("classrooms").select("*").eq("teacher_id", teacher_id).execute()
        )
        return [ClassroomRecord(**r) for r in rows]

    def list_classrooms_for_student(self, student_id: str) -> list[ClassroomRecord]:
        enr = self._rows(
            self.client.table("enrollments")
            .select("classroom_id")
            .eq("student_id", student_id)
            .execute()
        )
        ids = [e["classroom_id"] for e in enr]
        if not ids:
            return []
        rows = self._rows(
            self.client.table("classrooms").select("*").in_("id", ids).execute()
        )
        return [ClassroomRecord(**r) for r in rows]

    def count_students(self, classroom_id: str) -> int:
        resp = (
            self.client.table("enrollments")
            .select("student_id", count="exact")
            .eq("classroom_id", classroom_id)
            .execute()
        )
        return resp.count or 0

    def list_student_ids(self, classroom_id: str) -> list[str]:
        rows = self._rows(
            self.client.table("enrollments")
            .select("student_id")
            .eq("classroom_id", classroom_id)
            .execute()
        )
        return [r["student_id"] for r in rows]

    def enroll(self, classroom_id: str, student_id: str) -> None:
        self.client.table("enrollments").upsert(
            {"classroom_id": classroom_id, "student_id": student_id}
        ).execute()

    def is_enrolled(self, classroom_id: str, student_id: str) -> bool:
        row = self._one(
            self.client.table("enrollments")
            .select("student_id")
            .eq("classroom_id", classroom_id)
            .eq("student_id", student_id)
            .limit(1)
            .execute()
        )
        return row is not None

    # --- prompts ---
    def create_prompt(
        self,
        classroom_id: str,
        topic: str,
        learning_objectives: list[str],
        assessment: dict[str, Any],
        language: str,
    ) -> PromptRecord:
        row = self._one(
            self.client.table("prompts")
            .insert(
                {
                    "classroom_id": classroom_id,
                    "topic": topic,
                    "learning_objectives": learning_objectives,
                    "assessment": assessment,
                    "language": language,
                }
            )
            .execute()
        )
        return PromptRecord(**row)

    def get_prompt(self, prompt_id: str) -> PromptRecord | None:
        row = self._one(
            self.client.table("prompts").select("*").eq("id", prompt_id).limit(1).execute()
        )
        return PromptRecord(**row) if row else None

    def list_prompts_for_class(self, classroom_id: str) -> list[PromptRecord]:
        rows = self._rows(
            self.client.table("prompts").select("*").eq("classroom_id", classroom_id).execute()
        )
        return [PromptRecord(**r) for r in rows]

    # --- books ---
    def create_book(
        self, student_id: str, classroom_id: str | None, prompt_id: str | None
    ) -> BookRecord:
        row = self._one(
            self.client.table("books")
            .insert(
                {
                    "student_id": student_id,
                    "classroom_id": classroom_id,
                    "prompt_id": prompt_id,
                    "status": "planning",
                }
            )
            .execute()
        )
        return BookRecord(**row)

    def get_book(self, book_id: str) -> BookRecord | None:
        row = self._one(
            self.client.table("books").select("*").eq("id", book_id).limit(1).execute()
        )
        return BookRecord(**row) if row else None

    def update_book(self, book_id: str, **fields: Any) -> BookRecord:
        # 모든 변경은 마지막 활동 시각을 갱신한다(빈 변경=updated_at 만 갱신).
        payload = {**fields, "updated_at": now_iso()}
        row = self._one(
            self.client.table("books").update(payload).eq("id", book_id).execute()
        )
        return BookRecord(**row)

    def list_books_for_student(self, student_id: str) -> list[BookRecord]:
        rows = self._rows(
            self.client.table("books")
            .select("*")
            .eq("student_id", student_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return [BookRecord(**r) for r in rows]

    def list_books_for_class(self, classroom_id: str) -> list[BookRecord]:
        rows = self._rows(
            self.client.table("books")
            .select("*")
            .eq("classroom_id", classroom_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return [BookRecord(**r) for r in rows]

    # --- bibles ---
    def upsert_bible(self, book_id: str, data: dict[str, Any]) -> BibleRecord:
        row = self._one(
            self.client.table("bibles").upsert({"book_id": book_id, "data": data}).execute()
        )
        return BibleRecord(**row) if row else BibleRecord(book_id=book_id, data=data)

    def get_bible(self, book_id: str) -> BibleRecord | None:
        row = self._one(
            self.client.table("bibles").select("*").eq("book_id", book_id).limit(1).execute()
        )
        return BibleRecord(**row) if row else None

    # --- chapters ---
    def create_chapter(self, book_id: str, idx: int, mode: str) -> ChapterRecord:
        row = self._one(
            self.client.table("chapters")
            .insert({"book_id": book_id, "idx": idx, "mode": mode})
            .execute()
        )
        return ChapterRecord(**row)

    def get_chapter(self, book_id: str, idx: int) -> ChapterRecord | None:
        row = self._one(
            self.client.table("chapters")
            .select("*")
            .eq("book_id", book_id)
            .eq("idx", idx)
            .limit(1)
            .execute()
        )
        return ChapterRecord(**row) if row else None

    def list_chapters(self, book_id: str) -> list[ChapterRecord]:
        rows = self._rows(
            self.client.table("chapters")
            .select("*")
            .eq("book_id", book_id)
            .order("idx")
            .execute()
        )
        return [ChapterRecord(**r) for r in rows]

    def update_chapter(self, chapter_id: str, **fields: Any) -> ChapterRecord:
        row = self._one(
            self.client.table("chapters").update(fields).eq("id", chapter_id).execute()
        )
        return ChapterRecord(**row)

    # --- plan messages ---
    def add_plan_message(self, book_id: str, role: str, content: str) -> PlanMessageRecord:
        row = self._one(
            self.client.table("plan_messages")
            .insert({"book_id": book_id, "role": role, "content": content})
            .execute()
        )
        return PlanMessageRecord(**row)

    def list_plan_messages(self, book_id: str) -> list[PlanMessageRecord]:
        rows = self._rows(
            self.client.table("plan_messages")
            .select("*")
            .eq("book_id", book_id)
            .order("created_at")
            .execute()
        )
        return [PlanMessageRecord(**r) for r in rows]

    # --- RAG chunks ---
    def add_chunk(
        self, book_id: str, chapter_id: str | None, content: str, embedding: list[float]
    ) -> ChunkRecord:
        row = self._one(
            self.client.table("chapter_chunks")
            .insert(
                {
                    "book_id": book_id,
                    "chapter_id": chapter_id,
                    "content": content,
                    "embedding": embedding,
                }
            )
            .execute()
        )
        return ChunkRecord(**row) if row else ChunkRecord(
            id="", book_id=book_id, chapter_id=chapter_id, content=content, embedding=embedding
        )

    def search_chunks(
        self, book_id: str, query_embedding: list[float], k: int = 5
    ) -> list[ChunkRecord]:
        # 1순위: pgvector HNSW RPC(match_chunks). 실패 시 Python 코사인 폴백.
        try:
            resp = self.client.rpc(
                "match_chunks",
                {"p_book_id": book_id, "p_query": query_embedding, "p_k": k},
            ).execute()
            rows = self._rows(resp)
            return [
                ChunkRecord(
                    id=r["id"],
                    book_id=r["book_id"],
                    chapter_id=r.get("chapter_id"),
                    content=r["content"],
                    embedding=[],
                )
                for r in rows
            ]
        except Exception:
            rows = self._rows(
                self.client.table("chapter_chunks")
                .select("*")
                .eq("book_id", book_id)
                .execute()
            )
            scored = [
                (cosine_similarity(query_embedding, r.get("embedding") or []), r) for r in rows
            ]
            scored.sort(key=lambda t: t[0], reverse=True)
            return [
                ChunkRecord(
                    id=r["id"],
                    book_id=r["book_id"],
                    chapter_id=r.get("chapter_id"),
                    content=r["content"],
                    embedding=r.get("embedding") or [],
                )
                for _, r in scored[:k]
            ]

    # --- safety ---
    def add_safety_flag(
        self,
        book_id: str | None,
        student_id: str | None,
        source: str,
        reason: str,
        category: str | None = None,
        severity: str = "normal",
        letter_id: str | None = None,
    ) -> SafetyFlagRecord:
        row = self._one(
            self.client.table("safety_flags")
            .insert(
                {
                    "book_id": book_id,
                    "student_id": student_id,
                    "source": source,
                    "reason": reason,
                    "status": "open",
                    "category": category,
                    "severity": severity,
                    "letter_id": letter_id,
                }
            )
            .execute()
        )
        return SafetyFlagRecord(**row) if row else SafetyFlagRecord(
            id="", book_id=book_id, student_id=student_id, source=source, reason=reason,
            category=category, severity=severity, letter_id=letter_id, created_at=now_iso(),
        )

    def _class_book_ids(self, class_id: str) -> list[str]:
        rows = self._rows(
            self.client.table("books").select("id").eq("classroom_id", class_id).execute()
        )
        return [r["id"] for r in rows]

    def get_safety_flag(self, flag_id: str) -> SafetyFlagRecord | None:
        row = self._one(
            self.client.table("safety_flags").select("*").eq("id", flag_id).limit(1).execute()
        )
        return SafetyFlagRecord(**row) if row else None

    def list_safety_flags(
        self,
        class_id: str | None = None,
        book_id: str | None = None,
        status: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[SafetyFlagRecord]:
        q = self.client.table("safety_flags").select("*")
        if book_id is not None:
            q = q.eq("book_id", book_id)
        if class_id is not None:
            ids = self._class_book_ids(class_id)
            if not ids:
                return []
            q = q.in_("book_id", ids)
        if status is not None:
            q = q.eq("status", status)
        if source is not None:
            q = q.eq("source", source)
        rows = self._rows(q.order("created_at", desc=True).limit(limit).execute())
        return [SafetyFlagRecord(**r) for r in rows]

    def update_safety_flag(self, flag_id: str, **fields: Any) -> SafetyFlagRecord:
        row = self._one(
            self.client.table("safety_flags").update(fields).eq("id", flag_id).execute()
        )
        return SafetyFlagRecord(**row)

    # --- letters ---
    def add_letter(
        self,
        book_id: str,
        student_id: str | None,
        recipient: str,
        body: str,
        status: str = "pending",
        reply: str | None = None,
        reply_source: str | None = None,
    ) -> LetterRecord:
        row = self._one(
            self.client.table("letters")
            .insert(
                {
                    "book_id": book_id, "student_id": student_id, "recipient": recipient,
                    "body": body, "status": status, "reply": reply, "reply_source": reply_source,
                }
            )
            .execute()
        )
        return LetterRecord(**row)

    def get_letter(self, letter_id: str) -> LetterRecord | None:
        row = self._one(
            self.client.table("letters").select("*").eq("id", letter_id).limit(1).execute()
        )
        return LetterRecord(**row) if row else None

    def list_letters(
        self,
        class_id: str | None = None,
        book_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[LetterRecord]:
        q = self.client.table("letters").select("*")
        if book_id is not None:
            q = q.eq("book_id", book_id)
        if class_id is not None:
            ids = self._class_book_ids(class_id)
            if not ids:
                return []
            q = q.in_("book_id", ids)
        if status is not None:
            q = q.eq("status", status)
        rows = self._rows(q.order("created_at", desc=True).limit(limit).execute())
        return [LetterRecord(**r) for r in rows]

    def update_letter(self, letter_id: str, **fields: Any) -> LetterRecord:
        row = self._one(
            self.client.table("letters").update(fields).eq("id", letter_id).execute()
        )
        return LetterRecord(**row)

    # --- events ---
    def add_events(self, student_id: str, items: list[dict[str, Any]]) -> int:
        if not items:
            return 0
        payload = [
            {
                "book_id": it.get("book_id"),
                "student_id": student_id,
                "type": it["type"],
                "payload": it.get("payload") or {},
            }
            for it in items
        ]
        rows = self._rows(self.client.table("events").insert(payload).execute())
        return len(rows) if rows else len(payload)

    def list_events(
        self,
        class_id: str | None = None,
        book_id: str | None = None,
        student_id: str | None = None,
        type: str | None = None,
        since: str | None = None,
        limit: int = 1000,
    ) -> list[EventRecord]:
        q = self.client.table("events").select("*")
        if book_id is not None:
            q = q.eq("book_id", book_id)
        if class_id is not None:
            ids = self._class_book_ids(class_id)
            if not ids:
                return []
            q = q.in_("book_id", ids)
        if student_id is not None:
            q = q.eq("student_id", student_id)
        if type is not None:
            q = q.eq("type", type)
        if since is not None:
            q = q.gte("created_at", since)
        rows = self._rows(q.order("created_at", desc=True).limit(limit).execute())
        return [EventRecord(**r) for r in rows]

    # --- learning_artifacts ---
    def add_learning_artifact(
        self, book_id: str, type: str, data: dict[str, Any], chapter_id: str | None = None
    ) -> LearningArtifactRecord:
        row = self._one(
            self.client.table("learning_artifacts")
            .insert({"book_id": book_id, "type": type, "data": data, "chapter_id": chapter_id})
            .execute()
        )
        return LearningArtifactRecord(**row)

    def list_learning_artifacts(
        self,
        book_id: str | None = None,
        class_id: str | None = None,
        type: str | None = None,
    ) -> list[LearningArtifactRecord]:
        q = self.client.table("learning_artifacts").select("*")
        if book_id is not None:
            q = q.eq("book_id", book_id)
        if class_id is not None:
            ids = self._class_book_ids(class_id)
            if not ids:
                return []
            q = q.in_("book_id", ids)
        if type is not None:
            q = q.eq("type", type)
        rows = self._rows(q.order("created_at", desc=True).execute())
        return [LearningArtifactRecord(**r) for r in rows]

    # --- 관리자 집계 ---
    def _count(self, table: str, **eq: Any) -> int:
        q = self.client.table(table).select("*", count="exact", head=True)
        for k, v in eq.items():
            q = q.eq(k, v)
        return q.execute().count or 0

    def usage_counts(self) -> dict[str, Any]:
        chapters_written = (
            self.client.table("chapters")
            .select("*", count="exact", head=True)
            .gt("char_count", 0)
            .execute()
            .count
            or 0
        )
        return {
            "users": {
                "total": self._count("profiles"),
                "students": self._count("profiles", role="student"),
                "teachers": self._count("profiles", role="teacher"),
                "admins": self._count("profiles", role="admin"),
            },
            "classrooms": self._count("classrooms"),
            "prompts": self._count("prompts"),
            "books": {
                "total": self._count("books"),
                "planning": self._count("books", status="planning"),
                "writing": self._count("books", status="writing"),
                "done": self._count("books", status="done"),
            },
            "chapters_written": chapters_written,
            "safety_flags": {
                "open": self._count("safety_flags", status="open"),
                "total": self._count("safety_flags"),
            },
        }

    # --- AI 세션 / ReAct 트레이스 ---
    def create_ai_session(
        self, book_id: str | None, role: str, model: str | None = None
    ) -> AiSessionRecord:
        row = self._one(
            self.client.table("ai_sessions")
            .insert({"book_id": book_id, "role": role, "model": model})
            .execute()
        )
        return AiSessionRecord(**row)

    def update_ai_session(self, session_id: str, **fields: Any) -> AiSessionRecord:
        row = self._one(
            self.client.table("ai_sessions").update(fields).eq("id", session_id).execute()
        )
        return AiSessionRecord(**row)

    def get_ai_session(self, session_id: str) -> AiSessionRecord | None:
        row = self._one(
            self.client.table("ai_sessions").select("*").eq("id", session_id).limit(1).execute()
        )
        return AiSessionRecord(**row) if row else None

    def list_ai_sessions(
        self, book_id: str | None = None, status: str | None = None, limit: int = 50
    ) -> list[AiSessionRecord]:
        q = self.client.table("ai_sessions").select("*")
        if book_id is not None:
            q = q.eq("book_id", book_id)
        if status is not None:
            q = q.eq("status", status)
        rows = self._rows(q.order("started_at", desc=True).limit(limit).execute())
        return [AiSessionRecord(**r) for r in rows]

    def add_ai_step(
        self, session_id: str, idx: int, thought: str | None, skill: str | None,
        args: dict[str, Any], observation: dict[str, Any],
        tokens_in: int = 0, tokens_out: int = 0, ms: int | None = None,
    ) -> AiStepRecord:
        row = self._one(
            self.client.table("ai_steps")
            .insert({
                "session_id": session_id, "idx": idx, "thought": thought, "skill": skill,
                "args": args or {}, "observation": observation or {},
                "tokens_in": tokens_in, "tokens_out": tokens_out, "ms": ms,
            })
            .execute()
        )
        return AiStepRecord(**row)

    def list_ai_steps(self, session_id: str) -> list[AiStepRecord]:
        rows = self._rows(
            self.client.table("ai_steps")
            .select("*").eq("session_id", session_id).order("idx").execute()
        )
        return [AiStepRecord(**r) for r in rows]

    # --- messages ---
    def add_message(
        self, book_id: str | None, user_id: str | None, role: str, kind: str,
        content: str, session_id: str | None = None,
    ) -> MessageRecord:
        row = self._one(
            self.client.table("messages")
            .insert({
                "book_id": book_id, "user_id": user_id, "role": role,
                "kind": kind, "content": content, "session_id": session_id,
            })
            .execute()
        )
        return MessageRecord(**row)

    def list_messages(self, book_id: str, kind: str | None = None) -> list[MessageRecord]:
        q = self.client.table("messages").select("*").eq("book_id", book_id)
        if kind is not None:
            q = q.eq("kind", kind)
        rows = self._rows(q.order("created_at").execute())
        return [MessageRecord(**r) for r in rows]

    # --- token_usage ---
    def add_token_usage(
        self, session_id: str | None, model: str,
        tokens_in: int = 0, tokens_out: int = 0, est_cost: float = 0.0,
    ) -> TokenUsageRecord:
        row = self._one(
            self.client.table("token_usage")
            .insert({
                "session_id": session_id, "model": model,
                "tokens_in": tokens_in, "tokens_out": tokens_out, "est_cost": est_cost,
            })
            .execute()
        )
        return self._token_usage_rec(row) if row else TokenUsageRecord(
            id="", session_id=session_id, model=model,
            tokens_in=tokens_in, tokens_out=tokens_out, est_cost=est_cost,
        )

    def _token_usage_rec(self, row: dict) -> TokenUsageRecord:
        return TokenUsageRecord(
            id=row["id"], session_id=row.get("session_id"), model=row["model"],
            tokens_in=row.get("tokens_in") or 0, tokens_out=row.get("tokens_out") or 0,
            est_cost=float(row.get("est_cost") or 0), created_at=row.get("created_at") or "",
        )

    def token_usage_summary(self, since: str | None = None) -> dict[str, Any]:
        q = self.client.table("token_usage").select("model, tokens_in, tokens_out, est_cost")
        if since is not None:
            q = q.gte("created_at", since)
        rows = self._rows(q.execute())
        by_model: dict[str, dict[str, Any]] = {}
        for r in rows:
            m = by_model.setdefault(
                r["model"], {"calls": 0, "tokens_in": 0, "tokens_out": 0, "est_cost": 0.0}
            )
            m["calls"] += 1
            m["tokens_in"] += r.get("tokens_in") or 0
            m["tokens_out"] += r.get("tokens_out") or 0
            m["est_cost"] += float(r.get("est_cost") or 0)
        return {
            "calls": len(rows),
            "tokens_in": sum(r.get("tokens_in") or 0 for r in rows),
            "tokens_out": sum(r.get("tokens_out") or 0 for r in rows),
            "est_cost": sum(float(r.get("est_cost") or 0) for r in rows),
            "by_model": by_model,
        }

    # --- notifications ---
    def create_notification(
        self, title: str, body: str | None = None, level: str = "info",
        target_user_id: str | None = None, target_role: str | None = None,
        is_broadcast: bool = False,
    ) -> NotificationRecord:
        row = self._one(
            self.client.table("notifications")
            .insert({
                "title": title, "body": body, "level": level,
                "target_user_id": target_user_id, "target_role": target_role,
                "is_broadcast": is_broadcast,
            })
            .execute()
        )
        return NotificationRecord(**row)

    def list_notifications(
        self, user_id: str, role: str, unread_only: bool = False, limit: int = 50
    ) -> list[NotificationRecord]:
        # PostgREST or_ 필터 주입 방지: 신뢰 못 할 값을 보간하기 전에 엄격 검증.
        # 검증 실패 시 해당 절을 빼고(브로드캐스트만) 안전하게 동작.
        clauses = ["is_broadcast.eq.true"]
        if _UUID_RE.fullmatch(user_id):
            clauses.append(f"target_user_id.eq.{user_id}")
        if role in _VALID_ROLES:
            clauses.append(f"target_role.eq.{role}")
        q = self.client.table("notifications").select("*").or_(",".join(clauses))
        if unread_only:
            q = q.is_("read_at", "null")
        rows = self._rows(q.order("created_at", desc=True).limit(limit).execute())
        return [NotificationRecord(**r) for r in rows]

    def mark_notification_read(self, notification_id: str, user_id: str) -> None:
        self.client.table("notifications").update({"read_at": now_iso()}).eq(
            "id", notification_id
        ).is_("read_at", "null").execute()

    # --- app_settings ---
    def get_setting(self, key: str) -> Any | None:
        row = self._one(
            self.client.table("app_settings").select("value").eq("key", key).limit(1).execute()
        )
        return row["value"] if row else None

    def set_setting(self, key: str, value: Any, updated_by: str | None = None) -> None:
        self.client.table("app_settings").upsert({
            "key": key, "value": value, "updated_by": updated_by, "updated_at": now_iso(),
        }).execute()

    def all_settings(self) -> dict[str, Any]:
        rows = self._rows(self.client.table("app_settings").select("key, value").execute())
        return {r["key"]: r["value"] for r in rows}

    # --- audit_log ---
    def add_audit(
        self, admin_id: str | None, action: str, target: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> AuditRecord:
        row = self._one(
            self.client.table("audit_log")
            .insert({
                "admin_id": admin_id, "action": action,
                "target": target, "detail": detail or {},
            })
            .execute()
        )
        return AuditRecord(**row)

    def list_audit(self, limit: int = 100) -> list[AuditRecord]:
        rows = self._rows(
            self.client.table("audit_log")
            .select("*").order("created_at", desc=True).limit(limit).execute()
        )
        return [AuditRecord(**r) for r in rows]

    # --- rate limit (무상태, 멀티 워커 정합) ---
    def rate_hit(self, bucket: str, user_id: str, window: float) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window)).isoformat()
        # 만료 행 정리(이 bucket/user) → 카운트가 곧 윈도 내 횟수가 된다.
        self.client.table("rate_hits").delete().eq("bucket", bucket).eq(
            "user_id", user_id
        ).lt("created_at", cutoff).execute()
        self.client.table("rate_hits").insert(
            {"bucket": bucket, "user_id": user_id}
        ).execute()
        resp = (
            self.client.table("rate_hits")
            .select("id", count="exact", head=True)
            .eq("bucket", bucket)
            .eq("user_id", user_id)
            .execute()
        )
        return resp.count or 0
