"""API 요청/응답 스키마 — 03-기능명세서 §4/§7 의 계약을 그대로 따른다(camelCase)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.models.base import CamelModel

Role = Literal["student", "teacher", "admin"]
BookStatus = Literal["planning", "writing", "done"]
ChapterMode = Literal["free", "guided"]
ReviewStatus = Literal["pending", "ok", "revising"]


# --- 인증 / 계정 ---
class Me(CamelModel):
    id: str
    email: str
    role: Role
    grade: int | None = None
    guardian_consent: bool = False
    needs_onboarding: bool = False
    # 학생이 온보딩(classCode)으로 가입한 학급. 교사·관리자·미가입 학생은 null. (03 §4.2)
    class_id: str | None = None
    class_name: str | None = None


class OnboardingRequest(CamelModel):
    role: Literal["student", "teacher"]
    # 학급 코드: 영숫자 4~12자만 허용(패턴 주입 방지). 대소문자 무시는 조회 시 정규화.
    class_code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]{4,12}$")
    guardian_consent: bool = False
    grade: int | None = Field(default=None, ge=1, le=12)


# --- 교사 / 발제 ---
class ClassSummary(CamelModel):
    id: str
    name: str
    school_id: str | None = None
    student_count: int = 0
    code: str | None = None


class ClassesResponse(CamelModel):
    classes: list[ClassSummary]


class Assessment(CamelModel):
    type: Literal["quiz", "essay", "none"] = "none"
    detail: str = ""


class CreatePromptRequest(CamelModel):
    topic: str = Field(min_length=1)
    learning_objectives: list[str] = Field(min_length=1)
    assessment: Assessment = Assessment()
    language: str = "ko"


class Prompt(CamelModel):
    id: str
    class_id: str
    topic: str
    learning_objectives: list[str]
    assessment: Assessment
    language: str
    created_at: str


class PromptsResponse(CamelModel):
    prompts: list[Prompt]


# --- 교사 대시보드 (FR-T2) ---
class DashboardStudent(CamelModel):
    student_id: str
    student_email: str
    book_id: str | None = None
    title: str | None = None
    status: BookStatus | None = None
    chapters_done: int = 0
    total_chapters: int | None = None


class ObjectiveAchievement(CamelModel):
    objective: str
    rate: float = 0.0


class DashboardSummary(CamelModel):
    student_count: int = 0
    books_started: int = 0
    books_done: int = 0
    completion_rate: float = 0.0  # book_finished 기준(과도기 status 폴백)
    vocab_count: int = 0
    # 추가기능 04 — 실데이터 지표
    revisit_rate: float = 0.0
    vocab_quiz_accuracy: float = 0.0
    objective_achievement: list[ObjectiveAchievement] = []
    essays_submitted: int = 0


class DashboardResponse(CamelModel):
    students: list[DashboardStudent] = []
    summary: DashboardSummary = DashboardSummary()


# --- 책 ---
class CreateBookRequest(CamelModel):
    prompt_id: str


class Book(CamelModel):
    id: str
    prompt_id: str | None = None
    class_id: str | None = None
    status: BookStatus
    title: str | None = None
    created_at: str


class BookSummary(CamelModel):
    # GET /books 목록 항목 (03 §4.2). 학생 "내 책/이어 읽기".
    id: str
    title: str | None = None
    status: BookStatus
    chapters_done: int = 0
    total_chapters_planned: int | None = None
    updated_at: str


class BooksResponse(CamelModel):
    books: list[BookSummary] = []


class ChapterMeta(CamelModel):
    idx: int
    mode: ChapterMode
    review_status: ReviewStatus
    has_illustration: bool = False


class BookDetail(CamelModel):
    id: str
    status: BookStatus
    title: str | None = None
    prompt_id: str | None = None
    class_id: str | None = None
    chapters: list[ChapterMeta] = []
    total_chapters_planned: int | None = None


# --- 기획 인터뷰 ---
class PlanMessageRequest(CamelModel):
    message: str = Field(min_length=1)


class CharacterDraft(CamelModel):
    name: str | None = None
    traits: list[str] = []


class PlanReply(CamelModel):
    reply: str
    character_draft: CharacterDraft = CharacterDraft()
    ready_to_write: bool = False


# --- 설계(Bible) ---
class DesignResponse(CamelModel):
    status: Literal["designing", "done"]
    total_chapters_planned: int | None = None


# --- 단어 도움 ---
class Word(CamelModel):
    term: str
    reading: str
    meaning: str


# --- 챕터 수정(P2) ---
class ReviseRequest(CamelModel):
    instruction: str = Field(min_length=1)


class ReviseResponse(CamelModel):
    status: Literal["revising"]


# --- 학습 활동(P3) — FR-S8~S12 ---
class QuizItem(CamelModel):
    question: str
    choices: list[str]
    answer_index: int = 0


class EssayBlank(CamelModel):
    prompt: str
    hints: list[str] = []


class EmotionPoint(CamelModel):
    chapter_idx: int
    label: str
    value: float


class LearningResponse(CamelModel):
    vocab: list[Word] = []
    quiz: list[QuizItem] = []
    essay_blanks: list[EssayBlank] = []
    emotion: list[EmotionPoint] = []


class LetterRequest(CamelModel):
    to: str = Field(min_length=1)
    body: str = Field(min_length=1)


class LetterResponse(CamelModel):
    status: Literal["answered", "held"]
    reply: str | None = None
    letter_id: str | None = None


# --- 안전·교사검토 (추가기능 03) ---
class Letter(CamelModel):
    id: str
    book_id: str
    student_id: str | None = None
    recipient: str
    body: str
    status: str  # pending|answered|held|approved|rejected
    reply: str | None = None
    reply_source: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    created_at: str = ""


class LettersResponse(CamelModel):
    letters: list[Letter] = []


class SafetyFlag(CamelModel):
    id: str
    book_id: str | None = None
    student_id: str | None = None
    source: str
    reason: str
    category: str | None = None
    severity: str = "normal"
    status: str  # open|reviewed|resolved
    letter_id: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    note: str | None = None
    created_at: str = ""


class SafetyFlagsResponse(CamelModel):
    flags: list[SafetyFlag] = []


class SafetyFlagDetail(SafetyFlag):
    letter: Letter | None = None


class ResolveRequest(CamelModel):
    note: str | None = None


class LetterApproveRequest(CamelModel):
    reply: str | None = None
    use_ai_reply: bool = False


class LetterRejectRequest(CamelModel):
    note: str | None = None


# --- 측정(추가기능 04) ---
class TrackEvent(CamelModel):
    book_id: str | None = None
    type: str = Field(min_length=1)
    payload: dict[str, Any] = {}
    client_ts: str | None = None


class EventsRequest(CamelModel):
    events: list[TrackEvent] = Field(min_length=1, max_length=50)


class EventsResponse(CamelModel):
    accepted: int = 0


class LearningResultCreate(CamelModel):
    type: Literal["quiz", "essay", "emotion"]
    data: dict[str, Any] = {}


class LearningResult(CamelModel):
    id: str
    type: str
    data: dict[str, Any] = {}
    created_at: str = ""


class LearningResultCreated(CamelModel):
    id: str
    type: str
    created_at: str = ""


class LearningResultsResponse(CamelModel):
    results: list[LearningResult] = []


class Ask(CamelModel):
    session_id: str
    question: str
    choices: list[str] = []
    allow_text: bool = True


# --- 관리자(FR-M1, 최소) ---
class UsersStat(CamelModel):
    total: int = 0
    students: int = 0
    teachers: int = 0
    admins: int = 0


class BooksStat(CamelModel):
    total: int = 0
    planning: int = 0
    writing: int = 0
    done: int = 0


class SafetyStat(CamelModel):
    open: int = 0
    total: int = 0


class LearningResultsStat(CamelModel):
    quiz: int = 0
    essay: int = 0
    emotion: int = 0
    letter: int = 0


class AdminUser(CamelModel):
    id: str
    email: str
    role: str
    class_id: str | None = None
    class_name: str | None = None
    grade: int | None = None
    guardian_consent: bool = False
    status: str = "active"
    created_at: str = ""


class AdminUsersResponse(CamelModel):
    users: list[AdminUser] = []


class AdminUserPatch(CamelModel):
    role: Role | None = None
    class_id: str | None = None
    guardian_consent: bool | None = None


class AdminMessage(CamelModel):
    id: str
    book_id: str | None = None
    user_id: str | None = None
    role: str
    kind: str
    content: str
    session_id: str | None = None
    created_at: str = ""


class AdminMessagesResponse(CamelModel):
    messages: list[AdminMessage] = []


class TokenUsageBucket(CamelModel):
    key: str
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    est_cost: float = 0.0


class TokenUsageResponse(CamelModel):
    group_by: str
    buckets: list[TokenUsageBucket] = []
    total: TokenUsageBucket = TokenUsageBucket(key="total")


class AdminSettingsResponse(CamelModel):
    settings: dict[str, Any] = {}
    env: dict[str, bool] = {}


class SettingPut(CamelModel):
    key: str | None = None
    value: Any | None = None
    settings: dict[str, Any] | None = None


class AdminUsageResponse(CamelModel):
    users: UsersStat = UsersStat()
    classrooms: int = 0
    prompts: int = 0
    books: BooksStat = BooksStat()
    chapters_written: int = 0
    safety_flags: SafetyStat = SafetyStat()
    # 추가기능 04 — 전체 지표
    completion_rate: float = 0.0
    revisit_rate: float = 0.0
    events_total: int = 0
    learning_results: LearningResultsStat = LearningResultsStat()


# --- AI 세션 / ReAct 트레이스 (관리자 관측 · 03 §4.2) ---
class AiStepView(CamelModel):
    idx: int
    thought: str | None = None
    skill: str | None = None
    args: dict[str, Any] = {}
    observation: dict[str, Any] = {}
    tokens_in: int = 0
    tokens_out: int = 0
    ms: int | None = None
    created_at: str = ""


class AiSessionView(CamelModel):
    id: str
    book_id: str | None = None
    role: str
    model: str | None = None
    status: str  # running|awaiting_user|done|error
    summary: str | None = None
    error: str | None = None
    started_at: str = ""
    ended_at: str | None = None
    # 추가기능 06 — 관리자 콘솔 enrich(목록)
    user_id: str | None = None
    user_email: str | None = None
    step_count: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None


class AiSessionsResponse(CamelModel):
    sessions: list[AiSessionView] = []


class AiSessionDetail(AiSessionView):
    steps: list[AiStepView] = []


class AnswerRequest(CamelModel):
    choice: str | None = None
    text: str | None = None


def serialize(model: CamelModel) -> dict[str, Any]:
    """응답 직렬화: camelCase alias 사용."""
    return model.model_dump(by_alias=True)
