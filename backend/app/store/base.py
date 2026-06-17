"""Store 추상 인터페이스 — InMemoryStore / SupabaseStore 가 구현한다."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

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

    # --- AI 세션 / ReAct 트레이스 (02·06 관측 가능성) ---
    @abstractmethod
    def create_ai_session(
        self, book_id: str | None, role: str, model: str | None = None
    ) -> AiSessionRecord: ...

    @abstractmethod
    def update_ai_session(self, session_id: str, **fields: Any) -> AiSessionRecord: ...

    @abstractmethod
    def get_ai_session(self, session_id: str) -> AiSessionRecord | None: ...

    @abstractmethod
    def list_ai_sessions(
        self,
        book_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[AiSessionRecord]: ...

    @abstractmethod
    def add_ai_step(
        self,
        session_id: str,
        idx: int,
        thought: str | None,
        skill: str | None,
        args: dict[str, Any],
        observation: dict[str, Any],
        tokens_in: int = 0,
        tokens_out: int = 0,
        ms: int | None = None,
    ) -> AiStepRecord: ...

    @abstractmethod
    def list_ai_steps(self, session_id: str) -> list[AiStepRecord]: ...

    # --- messages (기획/편지/튜터 통합) ---
    @abstractmethod
    def add_message(
        self,
        book_id: str | None,
        user_id: str | None,
        role: str,
        kind: str,
        content: str,
        session_id: str | None = None,
    ) -> MessageRecord: ...

    @abstractmethod
    def list_messages(
        self, book_id: str, kind: str | None = None
    ) -> list[MessageRecord]: ...

    # --- token_usage ---
    @abstractmethod
    def add_token_usage(
        self,
        session_id: str | None,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        est_cost: float = 0.0,
    ) -> TokenUsageRecord: ...

    @abstractmethod
    def token_usage_summary(self, since: str | None = None) -> dict[str, Any]: ...

    # --- notifications (00 §6) ---
    @abstractmethod
    def create_notification(
        self,
        title: str,
        body: str | None = None,
        level: str = "info",
        target_user_id: str | None = None,
        target_role: str | None = None,
        is_broadcast: bool = False,
    ) -> NotificationRecord: ...

    @abstractmethod
    def list_notifications(
        self, user_id: str, role: str, unread_only: bool = False, limit: int = 50
    ) -> list[NotificationRecord]: ...

    @abstractmethod
    def mark_notification_read(self, notification_id: str, user_id: str) -> None: ...

    # --- app_settings (00 §7) ---
    @abstractmethod
    def get_setting(self, key: str) -> Any | None: ...

    @abstractmethod
    def set_setting(self, key: str, value: Any, updated_by: str | None = None) -> None: ...

    @abstractmethod
    def all_settings(self) -> dict[str, Any]: ...

    # --- audit_log ---
    @abstractmethod
    def add_audit(
        self,
        admin_id: str | None,
        action: str,
        target: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> AuditRecord: ...

    @abstractmethod
    def list_audit(self, limit: int = 100) -> list[AuditRecord]: ...
