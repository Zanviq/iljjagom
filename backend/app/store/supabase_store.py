"""Supabase 저장소 — 서비스 롤 클라이언트(워커/서버)로 테이블에 접근한다.

서비스 롤은 RLS를 우회하므로, 접근 제어는 0002_rls.sql(유저 토큰 경로)와
서비스 계층의 권한 검사로 이중 보장한다. 본 클래스는 영속화만 담당.
"""
from __future__ import annotations

from typing import Any

from app.config import Settings
from app.store.base import Store
from app.store.records import (
    BibleRecord,
    BookRecord,
    ChapterRecord,
    ChunkRecord,
    ClassroomRecord,
    PlanMessageRecord,
    ProfileRecord,
    PromptRecord,
    SafetyFlagRecord,
)
from app.util import cosine_similarity, now_iso


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
        row = self._one(
            self.client.table("classrooms").select("*").ilike("code", code).limit(1).execute()
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
        row = self._one(
            self.client.table("books").update(fields).eq("id", book_id).execute()
        )
        return BookRecord(**row)

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
        self, book_id: str | None, student_id: str | None, source: str, reason: str
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
                }
            )
            .execute()
        )
        return SafetyFlagRecord(**row) if row else SafetyFlagRecord(
            id="", book_id=book_id, student_id=student_id, source=source, reason=reason,
            created_at=now_iso(),
        )
