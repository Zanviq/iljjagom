"""저장소 내부 레코드 — API 스키마와 분리된 영속 모델."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProfileRecord:
    id: str
    email: str
    role: str = "student"
    guardian_consent: bool = False
    grade: int | None = None
    created_at: str = ""


@dataclass
class SchoolRecord:
    id: str
    name: str
    created_at: str = ""


@dataclass
class ClassroomRecord:
    id: str
    teacher_id: str
    name: str
    code: str
    school_id: str | None = None
    created_at: str = ""


@dataclass
class PromptRecord:
    id: str
    classroom_id: str
    topic: str
    learning_objectives: list[str]
    assessment: dict[str, Any]
    language: str = "ko"
    created_at: str = ""


@dataclass
class BookRecord:
    id: str
    student_id: str
    classroom_id: str | None
    prompt_id: str | None
    status: str = "planning"
    title: str | None = None
    total_chapters_planned: int | None = None
    created_at: str = ""
    updated_at: str = ""  # 마지막 활동 시각(이어 읽기 정렬용). GET /books.updatedAt.


@dataclass
class BibleRecord:
    book_id: str
    data: dict[str, Any]
    created_at: str = ""


@dataclass
class ChapterRecord:
    id: str
    book_id: str
    idx: int
    mode: str = "free"
    body: str = ""
    illustration_path: str | None = None
    review_status: str = "pending"
    words: list[str] = field(default_factory=list)
    char_count: int = 0
    created_at: str = ""


@dataclass
class PlanMessageRecord:
    id: str
    book_id: str
    role: str  # 'student' | 'interviewer'
    content: str
    created_at: str = ""


@dataclass
class ChunkRecord:
    id: str
    book_id: str
    chapter_id: str | None
    content: str
    embedding: list[float]
    created_at: str = ""


@dataclass
class SafetyFlagRecord:
    id: str
    book_id: str | None
    student_id: str | None
    source: str
    reason: str
    status: str = "open"
    created_at: str = ""


# --- 추가기능(03): 관측 가능성 / 알림 / 설정 / 감사 ---


@dataclass
class AiSessionRecord:
    id: str
    book_id: str | None
    role: str  # designer|writer|editor|chat|letter ...
    model: str | None = None
    status: str = "running"  # running|awaiting_user|done|error
    summary: str | None = None
    error: str | None = None
    started_at: str = ""
    ended_at: str | None = None


@dataclass
class AiStepRecord:
    id: str
    session_id: str
    idx: int
    thought: str | None = None
    skill: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    observation: dict[str, Any] = field(default_factory=dict)
    tokens_in: int = 0
    tokens_out: int = 0
    ms: int | None = None
    created_at: str = ""


@dataclass
class MessageRecord:
    id: str
    book_id: str | None
    user_id: str | None
    role: str  # user|ai|system
    kind: str = "plan"  # plan|letter|tutor ...
    content: str = ""
    session_id: str | None = None
    created_at: str = ""


@dataclass
class TokenUsageRecord:
    id: str
    session_id: str | None
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    est_cost: float = 0.0
    created_at: str = ""


@dataclass
class NotificationRecord:
    id: str
    target_user_id: str | None = None
    target_role: str | None = None
    is_broadcast: bool = False
    title: str = ""
    body: str | None = None
    level: str = "info"  # info|warn|error
    read_at: str | None = None
    created_at: str = ""


@dataclass
class AuditRecord:
    id: str
    admin_id: str | None
    action: str
    target: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
