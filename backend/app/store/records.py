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
    status: str = "active"  # active|deactivated (추가기능 06)
    display_name: str | None = None  # 표시 이름(0015) — user_metadata 또는 이메일 local-part
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
    # 학급 게시판 자동공개 토글(학생/15 §4, 기본 false=승인 후 공개).
    board_auto_publish: bool = False
    created_at: str = ""


@dataclass
class PromptRecord:
    id: str
    classroom_id: str
    topic: str
    learning_objectives: list[str]
    assessment: dict[str, Any]
    language: str = "ko"
    # 발제 옵션(선생님/02): 권장 학년·장수·마감·상태·발제별 안전강도 오버라이드.
    grade_band: int | None = None
    chapters_planned: int | None = None
    due_at: str | None = None
    status: str = "open"  # 'open' | 'closed'
    safety_level: str | None = None
    created_at: str = ""


@dataclass
class ClassSettingsRecord:
    classroom_id: str
    value: dict[str, Any] = field(default_factory=dict)
    updated_by: str | None = None
    updated_at: str = ""


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
    # 백그라운드 선생성(prefetch)으로 본문만 채워졌고 학생이 아직 진입하지 않은 상태(학생/06).
    # 학생 진입(스트림) 시 False 로 풀린다. chaptersDone 집계에서 제외(진척 과대 방지).
    prefetched: bool = False
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


# 자유집필 협업(학생/15 §2): 좌 본문(문단)·우 대화(턴).
@dataclass
class ParagraphRecord:
    id: str
    chapter_id: str
    book_id: str
    seq: int
    body: str
    source: str = "collab"  # 'collab' | 'ai' | 'revise'
    created_at: str = ""


@dataclass
class WritingTurnRecord:
    id: str
    chapter_id: str
    book_id: str
    role: str  # 'student' | 'writer'
    kind: str = "message"  # 'message' | 'question' | 'coaching'
    content: str = ""
    paragraph_id: str | None = None
    created_at: str = ""


# 학급 게시판(학생/15 §4).
@dataclass
class ClassPostRecord:
    id: str
    classroom_id: str
    book_id: str
    student_id: str
    title: str
    intro: str | None = None
    snapshot: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # 'pending' | 'published' | 'rejected'
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    review_note: str | None = None
    created_at: str = ""


@dataclass
class SafetyFlagRecord:
    id: str
    book_id: str | None
    student_id: str | None
    source: str  # letter|revise|plan|output|image
    reason: str
    status: str = "open"  # open|reviewed|resolved
    category: str | None = None  # violence|hate|sexual|self_harm|profanity ...
    severity: str = "normal"  # normal|high
    letter_id: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    note: str | None = None
    created_at: str = ""


@dataclass
class EventRecord:
    id: str
    book_id: str | None
    student_id: str | None
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class LearningArtifactRecord:
    id: str
    book_id: str
    type: str  # vocab|quiz|essay|letter|emotion
    data: dict[str, Any] = field(default_factory=dict)
    chapter_id: str | None = None
    created_at: str = ""


@dataclass
class LetterRecord:
    id: str
    book_id: str
    student_id: str | None
    recipient: str
    body: str
    status: str = "pending"  # pending|answered|held|approved|rejected
    reply: str | None = None
    reply_source: str | None = None  # ai|teacher
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    created_at: str = ""


# --- 추가기능(03): 관측 가능성 / 알림 / 설정 / 감사 ---


@dataclass
class AiSessionRecord:
    id: str
    book_id: str | None
    role: str  # designer|writer|editor|chat|overseer|letter ...
    model: str | None = None
    status: str = "running"  # running|awaiting_user|done|error
    summary: str | None = None
    error: str | None = None
    started_at: str = ""
    ended_at: str | None = None
    # 총괄(overseer) 세션처럼 book 이 없는 세션의 사용자 귀속(0014). book 세션은 None.
    user_id: str | None = None


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
