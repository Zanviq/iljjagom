"""인메모리 저장소 — 외부 키 없이 계약을 end-to-end 로 실행/테스트하기 위한 구현.

영속성은 없다(프로세스 메모리). 접근 제어(RLS 등가)는 서비스 계층이 담당한다.
"""
from __future__ import annotations

from typing import Any

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
