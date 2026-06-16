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
