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
    EventRecord,
    LearningArtifactRecord,
    LetterRecord,
    MessageRecord,
    NotificationRecord,
    ParagraphRecord,
    PlanMessageRecord,
    ProfileRecord,
    PromptRecord,
    SafetyFlagRecord,
    TokenUsageRecord,
    WritingTurnRecord,
)


class Store(ABC):
    # --- profiles ---
    @abstractmethod
    def get_profile(self, user_id: str) -> ProfileRecord | None: ...

    @abstractmethod
    def upsert_profile(self, profile: ProfileRecord) -> ProfileRecord: ...

    @abstractmethod
    def list_profiles(
        self, query: str | None = None, role: str | None = None, limit: int = 200
    ) -> list[ProfileRecord]: ...

    @abstractmethod
    def update_profile_fields(self, user_id: str, **fields: Any) -> ProfileRecord: ...

    @abstractmethod
    def count_profiles_by_role(self, role: str) -> int: ...

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

    # --- 자유집필 협업 (문단·턴, 학생/15 §2) ---
    @abstractmethod
    def add_paragraph(
        self, chapter_id: str, book_id: str, seq: int, body: str, source: str = "collab"
    ) -> ParagraphRecord: ...

    @abstractmethod
    def list_paragraphs(self, chapter_id: str) -> list[ParagraphRecord]: ...

    @abstractmethod
    def add_writing_turn(
        self, chapter_id: str, book_id: str, role: str, kind: str, content: str,
        paragraph_id: str | None = None,
    ) -> WritingTurnRecord: ...

    @abstractmethod
    def list_writing_turns(self, chapter_id: str) -> list[WritingTurnRecord]: ...

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
        self,
        book_id: str | None,
        student_id: str | None,
        source: str,
        reason: str,
        category: str | None = None,
        severity: str = "normal",
        letter_id: str | None = None,
    ) -> SafetyFlagRecord: ...

    @abstractmethod
    def get_safety_flag(self, flag_id: str) -> SafetyFlagRecord | None: ...

    @abstractmethod
    def list_safety_flags(
        self,
        class_id: str | None = None,
        book_id: str | None = None,
        status: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[SafetyFlagRecord]: ...

    @abstractmethod
    def update_safety_flag(self, flag_id: str, **fields: Any) -> SafetyFlagRecord: ...

    # --- letters (교사 검토 루프) ---
    @abstractmethod
    def add_letter(
        self,
        book_id: str,
        student_id: str | None,
        recipient: str,
        body: str,
        status: str = "pending",
        reply: str | None = None,
        reply_source: str | None = None,
    ) -> LetterRecord: ...

    @abstractmethod
    def get_letter(self, letter_id: str) -> LetterRecord | None: ...

    @abstractmethod
    def list_letters(
        self,
        class_id: str | None = None,
        book_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[LetterRecord]: ...

    @abstractmethod
    def update_letter(self, letter_id: str, **fields: Any) -> LetterRecord: ...

    # --- events (행동 로그, 04) ---
    @abstractmethod
    def add_events(self, student_id: str, items: list[dict[str, Any]]) -> int:
        """배치 적재. items=[{book_id, type, payload}]. 적재 수 반환."""
        ...

    @abstractmethod
    def list_events(
        self,
        class_id: str | None = None,
        book_id: str | None = None,
        student_id: str | None = None,
        type: str | None = None,
        since: str | None = None,
        limit: int = 1000,
    ) -> list[EventRecord]: ...

    # --- learning_artifacts (학습결과, 04 — 신규 테이블 대신 재사용) ---
    @abstractmethod
    def add_learning_artifact(
        self, book_id: str, type: str, data: dict[str, Any], chapter_id: str | None = None
    ) -> LearningArtifactRecord: ...

    @abstractmethod
    def list_learning_artifacts(
        self,
        book_id: str | None = None,
        class_id: str | None = None,
        type: str | None = None,
    ) -> list[LearningArtifactRecord]: ...

    # --- 관리자 집계 ---
    @abstractmethod
    def usage_counts(self) -> dict[str, Any]: ...

    # --- AI 세션 / ReAct 트레이스 (02·06 관측 가능성) ---
    @abstractmethod
    def create_ai_session(
        self, book_id: str | None, role: str, model: str | None = None,
        user_id: str | None = None,
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
        role: str | None = None,
        since: str | None = None,
        until: str | None = None,
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

    @abstractmethod
    def list_messages_for_session(self, session_id: str) -> list[MessageRecord]:
        """한 AI 세션(session_id)에 속한 대화 메시지(시간순). overseer 대화 연속용."""
        ...

    @abstractmethod
    def list_messages_admin(
        self,
        user_id: str | None = None,
        book_id: str | None = None,
        kind: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 100,
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

    @abstractmethod
    def token_usage_buckets(
        self, group_by: str = "model", since: str | None = None, until: str | None = None
    ) -> dict[str, Any]:
        """groupBy(model|role|day) 별 토큰/비용 집계. {buckets:[{key,calls,...}], total}."""
        ...

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

    # --- backup (06 §3.9) ---
    @abstractmethod
    def export_tables(self, tables: list[str]) -> dict[str, list[dict[str, Any]]]: ...

    @abstractmethod
    def import_tables(
        self, mode: str, tables: dict[str, list[dict[str, Any]]]
    ) -> dict[str, int]: ...

    # --- rate limit (무상태화, §3.4) ---
    @abstractmethod
    def rate_hit(self, bucket: str, user_id: str, window: float) -> int:
        """이 (bucket, user) 호출을 1 기록하고, window 초 내 현재 카운트를 반환."""
        ...
