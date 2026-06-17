"""Store 추상 인터페이스 — InMemoryStore / SupabaseStore 가 구현한다."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

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


class Store(ABC):
    # --- profiles ---
    @abstractmethod
    def get_profile(self, user_id: str) -> ProfileRecord | None: ...

    @abstractmethod
    def upsert_profile(self, profile: ProfileRecord) -> ProfileRecord: ...

    # --- classrooms / enrollments ---
    @abstractmethod
    def create_classroom(
        self, teacher_id: str, name: str, code: str, school_id: str | None = None
    ) -> ClassroomRecord: ...

    @abstractmethod
    def get_classroom(self, classroom_id: str) -> ClassroomRecord | None: ...

    @abstractmethod
    def get_classroom_by_code(self, code: str) -> ClassroomRecord | None: ...

    @abstractmethod
    def list_classrooms_for_teacher(self, teacher_id: str) -> list[ClassroomRecord]: ...

    @abstractmethod
    def list_classrooms_for_student(self, student_id: str) -> list[ClassroomRecord]: ...

    @abstractmethod
    def count_students(self, classroom_id: str) -> int: ...

    @abstractmethod
    def list_student_ids(self, classroom_id: str) -> list[str]: ...

    @abstractmethod
    def enroll(self, classroom_id: str, student_id: str) -> None: ...

    @abstractmethod
    def is_enrolled(self, classroom_id: str, student_id: str) -> bool: ...

    # --- prompts ---
    @abstractmethod
    def create_prompt(
        self,
        classroom_id: str,
        topic: str,
        learning_objectives: list[str],
        assessment: dict[str, Any],
        language: str,
    ) -> PromptRecord: ...

    @abstractmethod
    def get_prompt(self, prompt_id: str) -> PromptRecord | None: ...

    @abstractmethod
    def list_prompts_for_class(self, classroom_id: str) -> list[PromptRecord]: ...

    # --- books ---
    @abstractmethod
    def create_book(
        self, student_id: str, classroom_id: str | None, prompt_id: str | None
    ) -> BookRecord: ...

    @abstractmethod
    def get_book(self, book_id: str) -> BookRecord | None: ...

    @abstractmethod
    def update_book(self, book_id: str, **fields: Any) -> BookRecord: ...

    @abstractmethod
    def list_books_for_student(self, student_id: str) -> list[BookRecord]: ...

    @abstractmethod
    def list_books_for_class(self, classroom_id: str) -> list[BookRecord]: ...

    # --- bibles ---
    @abstractmethod
    def upsert_bible(self, book_id: str, data: dict[str, Any]) -> BibleRecord: ...

    @abstractmethod
    def get_bible(self, book_id: str) -> BibleRecord | None: ...

    # --- chapters ---
    @abstractmethod
    def create_chapter(self, book_id: str, idx: int, mode: str) -> ChapterRecord: ...

    @abstractmethod
    def get_chapter(self, book_id: str, idx: int) -> ChapterRecord | None: ...

    @abstractmethod
    def list_chapters(self, book_id: str) -> list[ChapterRecord]: ...

    @abstractmethod
    def update_chapter(self, chapter_id: str, **fields: Any) -> ChapterRecord: ...

    # --- plan messages ---
    @abstractmethod
    def add_plan_message(self, book_id: str, role: str, content: str) -> PlanMessageRecord: ...

    @abstractmethod
    def list_plan_messages(self, book_id: str) -> list[PlanMessageRecord]: ...

    # --- RAG chunks ---
    @abstractmethod
    def add_chunk(
        self, book_id: str, chapter_id: str | None, content: str, embedding: list[float]
    ) -> ChunkRecord: ...

    @abstractmethod
    def search_chunks(
        self, book_id: str, query_embedding: list[float], k: int = 5
    ) -> list[ChunkRecord]: ...

    # --- safety ---
    @abstractmethod
    def add_safety_flag(
        self, book_id: str | None, student_id: str | None, source: str, reason: str
    ) -> SafetyFlagRecord: ...

    # --- 관리자 집계 ---
    @abstractmethod
    def usage_counts(self) -> dict[str, Any]: ...
