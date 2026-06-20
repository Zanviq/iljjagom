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
    # 표시 이름(인사 개인화). display_name(user_metadata 또는 이메일 local-part), 없으면 null. (03 §4.2)
    name: str | None = None
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


# --- 다중 학급(P5, 선생님/01) ---
class CreateClassRequest(CamelModel):
    name: str = Field(min_length=1, max_length=60)


class UpdateClassRequest(CamelModel):
    name: str = Field(min_length=1, max_length=60)


class RotateCodeResponse(CamelModel):
    id: str
    code: str


class Assessment(CamelModel):
    type: Literal["quiz", "essay", "none"] = "none"
    detail: str = ""


SafetyLevel = Literal["relaxed", "standard", "strict"]


class CreatePromptRequest(CamelModel):
    topic: str = Field(min_length=1)
    learning_objectives: list[str] = Field(min_length=1)
    assessment: Assessment = Assessment()
    language: str = "ko"
    # 발제 옵션(선생님/02, 선택).
    grade_band: int | None = Field(default=None, ge=1, le=12)
    chapters_planned: int | None = Field(default=None, ge=1, le=20)
    due_at: str | None = None
    safety_level: SafetyLevel | None = None


class UpdatePromptRequest(CamelModel):
    topic: str | None = Field(default=None, min_length=1)
    learning_objectives: list[str] | None = None
    assessment: Assessment | None = None
    grade_band: int | None = Field(default=None, ge=1, le=12)
    chapters_planned: int | None = Field(default=None, ge=1, le=20)
    due_at: str | None = None
    status: Literal["open", "closed"] | None = None
    safety_level: SafetyLevel | None = None


class Prompt(CamelModel):
    id: str
    class_id: str
    topic: str
    learning_objectives: list[str]
    assessment: Assessment
    language: str
    grade_band: int | None = None
    chapters_planned: int | None = None
    due_at: str | None = None
    status: Literal["open", "closed"] = "open"
    safety_level: SafetyLevel | None = None
    created_at: str


class PromptsResponse(CamelModel):
    prompts: list[Prompt]


# --- 학급 설정 (선생님/02) ---
class ClassSettingsResponse(CamelModel):
    value: dict[str, Any] = {}
    defaults: dict[str, Any] = {}


class ClassSettingsPut(CamelModel):
    value: dict[str, Any] = {}


# --- 대시보드 시계열 (선생님/02) ---
class DashboardHistoryBucket(CamelModel):
    period_start: str
    active_students: int = 0
    chapters_done: int = 0
    books_finished: int = 0
    essays_submitted: int = 0


class DashboardHistory(CamelModel):
    buckets: list[DashboardHistoryBucket] = []
    totals: DashboardHistoryBucket = DashboardHistoryBucket(period_start="")


# --- 학생 데이터 열람 (선생님/03) ---
class ChapterContent(CamelModel):
    idx: int
    mode: ChapterMode
    review_status: ReviewStatus
    body: str = ""
    char_count: int = 0
    words: list[str] = []
    illustration_url: str | None = None
    updated_at: str | None = None


class ChaptersContentResponse(CamelModel):
    chapters: list[ChapterContent] = []


class PlanMessageView(CamelModel):
    role: str  # 'student' | 'interviewer'
    content: str
    created_at: str


class PlanMessagesResponse(CamelModel):
    messages: list[PlanMessageView] = []


class BibleResponse(CamelModel):
    bible: dict[str, Any] = {}


class StudentBooksResponse(CamelModel):
    books: list[BookSummary] = []


# --- 발제별 집계 (선생님/05) ---
class PromptSubmission(CamelModel):
    student_id: str
    student_email: str = ""
    book_id: str
    title: str | None = None
    status: BookStatus | None = None
    chapters_done: int = 0
    total_chapters_planned: int | None = None
    char_total: int = 0
    quiz_count: int = 0
    essay_count: int = 0
    emotion_logged: bool = False
    letter_count: int = 0
    last_activity_at: str | None = None


class PromptSubmissionCounts(CamelModel):
    enrolled: int = 0
    started: int = 0
    finished: int = 0


class PromptSubmissionStudent(CamelModel):
    student_id: str
    student_email: str = ""


class PromptSubmissionsResponse(CamelModel):
    prompt: Prompt
    counts: PromptSubmissionCounts = PromptSubmissionCounts()
    submissions: list[PromptSubmission] = []
    not_started: list[PromptSubmissionStudent] = []


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
    # 자유집필 협업 문단 수(학생/15). free 챕터: 0이면 협업 화면, 차 있으면 독서로 프론트 분기.
    paragraph_count: int = 0


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
    # 인터뷰 마무리 모드(ready 충족 → 새 질문 없이 공감만). 협업 화면 전환 신호(학생/03·15).
    interview_closed: bool = False


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


# --- 자유집필 협업(P2, 학생/15 §2) ---
class CollabRequest(CamelModel):
    message: str = Field(min_length=1, max_length=2000)
    # 직전 AI 지도(coaching) 제안을 받아들였는지. true 면 제안대로 생성.
    accept: bool = False


class CollabParagraph(CamelModel):
    seq: int
    body: str


class CollabCoaching(CamelModel):
    text: str
    reasons: list[str] = []


class CollabReply(CamelModel):
    kind: Literal["paragraph", "coaching", "error"]
    paragraph: CollabParagraph | None = None
    coaching: CollabCoaching | None = None
    question: str | None = None
    chapter_complete: bool = False
    message: str | None = None  # kind="error" 안내 문구
    replaced_seq: int | None = None  # 대화수정으로 교체된 문단 번호(05-기능수정 §02)
    suggestion: str | None = None  # 곰 작가의 대안 제안(있을 때만)


class CollabTurnView(CamelModel):
    role: Literal["student", "writer"]
    kind: Literal["message", "question", "coaching"]
    content: str
    created_at: str


class CollabParagraphView(CamelModel):
    seq: int
    body: str
    source: str


class CollabState(CamelModel):
    paragraphs: list[CollabParagraphView] = []
    turns: list[CollabTurnView] = []
    chapter_complete: bool = False


# --- 문단 직접편집·순서변경(05-기능수정 §02) ---
class ParagraphEditRequest(CamelModel):
    body: str


class ParagraphEditResult(CamelModel):
    paragraph: CollabParagraph
    suggestion: str | None = None  # 편집이 과하면 곰 작가 대안


class ParagraphReorderRequest(CamelModel):
    order: list[int]  # 새 순서(현재 seq 들의 순열)


class ParagraphReorderResult(CamelModel):
    paragraphs: list[CollabParagraphView] = []


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
    # 학생 입력 활동(학생/11): 미입력 장은 null. 라벨은 팔레트 화이트리스트 값.
    label: str | None = None
    value: float | None = None


class EmotionFrame(CamelModel):
    """감정 곡선 입력 틀 — 시스템 자동 곡선 대신 장 목록 + 라벨 팔레트(학생/11)."""
    labels: list[str] = []
    points: list[EmotionPoint] = []


class LetterCharacter(CamelModel):
    """편지 대상 인물 선택지(학생/12) — Bible characters 파생."""
    id: str
    name: str
    traits: list[str] = []


class LearningResponse(CamelModel):
    vocab: list[Word] = []
    quiz: list[QuizItem] = []
    essay_blanks: list[EssayBlank] = []
    emotion: EmotionFrame = EmotionFrame()
    letter_characters: list[LetterCharacter] = []


# --- 중간활동(P3, 학생/15 §3) ---
class MidActivityResponse(CamelModel):
    """기·승 완료 후 필수 중간활동(전·결 prefetch 동안 푸는 퀴즈/독후감)."""
    required: bool = False   # 기·승 완료 + 전·결 존재 + 미완료
    done: bool = False
    quiz: list[QuizItem] = []
    essay_blanks: list[EssayBlank] = []


class MidActivityComplete(CamelModel):
    # 완료 처리(선택적으로 학생 답안 동봉 가능 — 본문 검증은 learning-results 경로 사용).
    pass


# --- 학급 게시판(P4, 학생/15 §4 · 14) ---
class BoardPostCreate(CamelModel):
    intro: str | None = Field(default=None, max_length=2000)


class BoardPostCreated(CamelModel):
    post_id: str
    status: Literal["pending", "published", "rejected"]


class BoardPostSummary(CamelModel):
    id: str
    title: str
    student_name: str | None = None
    status: Literal["pending", "published", "rejected"]
    created_at: str
    snapshot: dict[str, Any] = {}


class BoardPost(CamelModel):
    id: str
    classroom_id: str
    book_id: str
    student_id: str
    title: str
    intro: str | None = None
    snapshot: dict[str, Any] = {}
    status: Literal["pending", "published", "rejected"]
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    review_note: str | None = None
    created_at: str


class BoardPostsResponse(CamelModel):
    posts: list[BoardPostSummary] = []


class BoardRejectRequest(CamelModel):
    note: str | None = Field(default=None, max_length=500)


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
    user_email: str | None = None  # 관리자/01 enrich
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


class Notification(CamelModel):
    id: str
    target_user_id: str | None = None
    target_role: str | None = None
    is_broadcast: bool = False
    title: str
    body: str | None = None
    level: str = "info"
    read_at: str | None = None
    created_at: str = ""


class NotificationsResponse(CamelModel):
    notifications: list[Notification] = []


class NotificationCreate(CamelModel):
    target_user_id: str | None = None
    target_role: Role | None = None
    is_broadcast: bool = False
    title: str = Field(min_length=1)
    body: str | None = None
    level: Literal["info", "warn", "error"] = "info"


class BackupExportRequest(CamelModel):
    tables: list[str] | None = None


class BackupExportResponse(CamelModel):
    exported_at: str
    tables: dict[str, list[dict[str, Any]]] = {}


class BackupImportRequest(CamelModel):
    mode: Literal["merge", "overwrite"] = "merge"
    tables: dict[str, list[dict[str, Any]]] = {}


class BackupImportResponse(CamelModel):
    imported: dict[str, int] = {}


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
    # 관리자/01 드릴다운 — 책 맥락·단계 라벨
    book_title: str | None = None
    book_status: str | None = None
    stage: str | None = None


class AiSessionsResponse(CamelModel):
    sessions: list[AiSessionView] = []


class SessionContext(CamelModel):
    user_email: str | None = None
    book_id: str | None = None
    book_title: str | None = None
    stage: str | None = None


class AiSessionDetail(AiSessionView):
    steps: list[AiStepView] = []
    # 관리자/01 — 세션 대화 전문 + 맥락
    transcript: list[AdminMessage] = []
    context: SessionContext = SessionContext()


# --- 관리자 드릴다운 (관리자/01) ---
class UserOverviewBook(CamelModel):
    id: str
    title: str | None = None
    status: BookStatus
    created_at: str = ""
    session_count: int = 0
    message_count: int = 0


class UserOverview(CamelModel):
    user: AdminUser
    books: list[UserOverviewBook] = []
    sessions: list[AiSessionView] = []
    recent_messages: list[AdminMessage] = []


class BookTimelineChapter(CamelModel):
    idx: int
    review_status: ReviewStatus
    char_count: int = 0


class BookTimeline(CamelModel):
    book: Book
    prompt: Prompt | None = None
    chapters: list[BookTimelineChapter] = []
    sessions: list[AiSessionView] = []
    plan_messages: list[PlanMessageView] = []
    messages: list[AdminMessage] = []
    learning: list[LearningResult] = []


class MessagesByUserRow(CamelModel):
    user_id: str
    email: str | None = None
    role: str | None = None
    message_count: int = 0
    book_count: int = 0
    last_at: str | None = None


class MessagesByUser(CamelModel):
    users: list[MessagesByUserRow] = []


class AnswerRequest(CamelModel):
    choice: str | None = None
    text: str | None = None


# --- 총괄(Overseer) AI (디자인 03 / 03-기능명세서 §4.2) ---
class OverseerMessageRequest(CamelModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    route: str | None = None


class OverseerAction(CamelModel):
    type: Literal["navigate"] = "navigate"
    to: str
    label: str
    auto: bool = False


class OverseerReply(CamelModel):
    session_id: str
    reply: str
    actions: list[OverseerAction] = []


def serialize(model: CamelModel) -> dict[str, Any]:
    """응답 직렬화: camelCase alias 사용."""
    return model.model_dump(by_alias=True)
