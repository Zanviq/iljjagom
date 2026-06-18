/**
 * 백엔드(FastAPI)와 공유하는 계약 타입.
 * 단일 원천: documents/for-claude/.../03-기능명세서.md §4(API)·§5(SSE)·§7(타입).
 * 필드/이름은 §4 응답 스키마를 그대로 따른다(camelCase). 계약을 바꾸려면 먼저 명세서를 고친다.
 */

export type Role = "student" | "teacher" | "admin";
export type BookStatus = "planning" | "writing" | "done";
export type ChapterMode = "free" | "guided";
export type ReviewStatus = "pending" | "ok" | "revising";
export type AssessmentType = "quiz" | "essay" | "none";

/** GET /me, POST /onboarding 응답 */
export interface Me {
  id: string;
  email: string;
  /** 표시 이름(=profiles.display_name). 온보딩 전이면 null. (2026-06-18 계약 추가) */
  name: string | null;
  role: Role;
  grade: number | null;
  guardianConsent: boolean;
  needsOnboarding: boolean;
  /** 학생이 가입한 학급(발제 진입점). 교사·관리자·미가입 학생은 null. (2026-06-16 계약 추가) */
  classId: string | null;
  className: string | null;
}

/** POST /onboarding 요청 */
export interface OnboardingRequest {
  role: "student" | "teacher";
  classCode: string | null;
  guardianConsent: boolean;
}

/** GET /classes 의 학급 항목 (code = 학생 가입 코드, 2026-06-16 추가) */
export interface ClassSummary {
  id: string;
  name: string;
  schoolId: string;
  studentCount: number;
  code: string;
}

export interface Assessment {
  type: AssessmentType;
  detail: string;
}

/** 발제 */
export interface Prompt {
  id: string;
  classId: string;
  topic: string;
  learningObjectives: string[];
  assessment: Assessment;
  language: string;
  createdAt: string;
}

/** POST /classes/{classId}/prompts 요청 */
export interface CreatePromptRequest {
  topic: string;
  learningObjectives: string[];
  assessment: Assessment;
  language: string;
}

/** 책 목차의 챕터 요약 (GET /books/{id} 의 chapters[]) */
export interface ChapterSummary {
  idx: number;
  mode: ChapterMode;
  reviewStatus: ReviewStatus;
  hasIllustration: boolean;
}

/** GET /books 의 책 항목 (내 책 목록/이어 읽기, §4.2) */
export interface BookSummary {
  id: string;
  title: string | null;
  status: BookStatus;
  /** 본문이 작성된(char_count>0) 챕터 수 */
  chaptersDone: number;
  /** 설계 전이면 null */
  totalChaptersPlanned: number | null;
  /** 마지막 활동 시각(ISO8601). 목록은 이 값 내림차순 */
  updatedAt: string;
}

/** POST /books 응답 */
export interface BookCreated {
  id: string;
  promptId: string;
  classId: string;
  status: BookStatus;
  title: string | null;
  createdAt: string;
}

/** GET /books/{id} 응답 */
export interface Book {
  id: string;
  status: BookStatus;
  title: string | null;
  promptId: string;
  classId: string;
  chapters: ChapterSummary[];
  totalChaptersPlanned: number;
}

/** POST /books/{id}/plan/messages 응답 */
export interface PlanReply {
  reply: string;
  characterDraft: {
    name: string | null;
    traits: string[];
  };
  readyToWrite: boolean;
  /** AI가 되물을 때(ask_user) 동기 흐름에 실려 옴(추가기능 02/04). */
  ask?: Ask | null;
}

/** POST /books/{id}/design 응답 */
export interface DesignStatus {
  status: "designing" | "done";
  totalChaptersPlanned: number;
}

/** GET /books/{id}/words 응답 */
export interface Word {
  term: string;
  reading: string;
  meaning: string;
}

/** GET /classes/{id}/dashboard 의 학생별 진척 (FR-T2) */
export interface DashboardStudent {
  studentId: string;
  studentEmail: string;
  bookId: string | null;
  title: string | null;
  status: BookStatus | null;
  chaptersDone: number;
  totalChapters: number;
}

/** GET /classes/{id}/dashboard 의 요약 집계 */
export interface DashboardSummary {
  studentCount: number;
  booksStarted: number;
  booksDone: number;
  /** 완독률 0~1 (추가기능 04: book_finished 기준, 과도기 status 폴백) */
  completionRate: number;
  vocabCount: number;
  /* 추가기능 04 확장(없을 수도 있어 optional) */
  revisitRate?: number;
  vocabQuizAccuracy?: number;
  objectiveAchievement?: { objective: string; rate: number }[];
  essaysSubmitted?: number;
}

/** GET /classes/{id}/dashboard 응답 (FR-T2) */
export interface Dashboard {
  students: DashboardStudent[];
  summary: DashboardSummary;
}

/** GET /books/{id}/learning 응답 (FR-S8~S12) */
export interface QuizItem {
  question: string;
  choices: string[];
  answerIndex: number;
}
export interface EssayBlank {
  prompt: string;
  hints: string[];
}
export interface EmotionPoint {
  chapterIdx: number;
  label: string;
  value: number;
}
export interface Learning {
  vocab: Word[];
  quiz: QuizItem[];
  essayBlanks: EssayBlank[];
  emotion: EmotionPoint[];
}

/** POST /books/{id}/letters 응답 (FR-S11). letterId 추가(추가기능 03). */
export interface LetterReply {
  status: "answered" | "held";
  reply: string | null;
  letterId: string;
}

/* ── 안전·교사검토 (추가기능 03, §4.2·§7) ── */
export type LetterStatus =
  | "pending"
  | "answered"
  | "held"
  | "approved"
  | "rejected";
export type SafetyFlagStatus = "open" | "resolved";

/** 인물 편지 원문·답장·검토 상태 */
export interface Letter {
  id: string;
  bookId: string;
  studentId: string;
  recipient: string;
  body: string;
  status: LetterStatus;
  reply?: string | null;
  replySource?: string | null;
  reviewedBy?: string | null;
  reviewedAt?: string | null;
  createdAt: string;
}

/** 안전 신호(safety_flags) */
export interface SafetyFlag {
  id: string;
  bookId: string | null;
  studentId: string | null;
  /** 발생 위치(입력/출력/편지 등) */
  source: string;
  reason: string;
  category?: string | null;
  severity: string;
  status: SafetyFlagStatus;
  letterId?: string | null;
  reviewedBy?: string | null;
  reviewedAt?: string | null;
  note?: string | null;
  createdAt: string;
}

/** GET /safety-flags/{id} 응답 = 신호 + 연결 편지 */
export interface SafetyFlagDetail extends SafetyFlag {
  letter?: Letter | null;
}

/** GET /admin/usage 응답 (FR-M1 최소 + 추가기능 04 확장) */
export interface AdminUsage {
  users: { total: number; students: number; teachers: number; admins: number };
  classrooms: number;
  prompts: number;
  books: { total: number; planning: number; writing: number; done: number };
  chaptersWritten: number;
  safetyFlags: { open: number; total: number };
  /* 추가기능 04 확장(optional) */
  completionRate?: number;
  revisitRate?: number;
  eventsTotal?: number;
  learningResults?: {
    quiz: number;
    essay: number;
    emotion: number;
    letter: number;
  };
}

/* ── 측정·학습결과 (추가기능 04, §4.2·§7) ── */
export type EventType =
  | "chapter_open"
  | "chapter_dwell"
  | "chapter_done"
  | "book_finished"
  | "word_touch"
  | "prompt_reveal"
  | "revise_request"
  | "learning_open"
  | "locale_toggle";

/** 행동 로그 1건(POST /events). payload 에 자유텍스트/본문 금지(word_touch term 만 예외). */
export interface TrackEvent {
  bookId?: string | null;
  type: EventType;
  payload?: Record<string, unknown>;
  clientTs: string;
}

export type LearningResultType = "quiz" | "essay" | "emotion";

/** 학습 결과 저장 요청(POST /books/{id}/learning-results). */
export interface LearningResultCreate {
  type: LearningResultType;
  data: unknown;
}

/** 저장된 학습 결과(GET). */
export interface LearningResult {
  id: string;
  type: string;
  data: unknown;
  createdAt: string;
}

/** ask_user 질문(SSE `ask` 이벤트 / PlanReply.ask). lib/ai.ts AskUserPrompt 와 동일 구조. */
export interface Ask {
  sessionId: string;
  question: string;
  choices: string[];
  allowText: boolean;
}

/* ── 관리자 콘솔 (추가기능 06, §4.2·§7) ── */
export interface AdminUser {
  id: string;
  email: string;
  role: Role;
  classId?: string | null;
  className?: string | null;
  grade?: number | null;
  guardianConsent: boolean;
  status: "active" | "deactivated";
  createdAt: string;
}
export interface AdminUserPatch {
  role?: Role;
  classId?: string | null;
  guardianConsent?: boolean;
}

export interface AdminMessage {
  id: string;
  bookId?: string | null;
  userId?: string | null;
  role: string;
  kind: string;
  content: string;
  sessionId?: string | null;
  createdAt: string;
}

export interface TokenUsageBucket {
  key: string;
  calls: number;
  tokensIn: number;
  tokensOut: number;
  estCost: number;
}
export interface TokenUsageReport {
  groupBy: string;
  buckets: TokenUsageBucket[];
  total: { calls: number; tokensIn: number; tokensOut: number; estCost: number };
}

export interface AdminSettingsResponse {
  settings: Record<string, unknown>;
  /** env 키 존재 여부만(값 비노출) */
  env: Record<string, boolean>;
}
export interface SettingPut {
  key?: string;
  value?: unknown;
  settings?: Record<string, unknown>;
}

export type NotificationLevel = "info" | "warn" | "error";
/** 알림 (DOM 전역 Notification 과 구분해 AppNotification). */
export interface AppNotification {
  id: string;
  targetUserId?: string | null;
  targetRole?: string | null;
  isBroadcast: boolean;
  title: string;
  body?: string | null;
  level: NotificationLevel;
  readAt?: string | null;
  createdAt: string;
}
export interface NotificationCreate {
  targetUserId?: string;
  targetRole?: string;
  isBroadcast?: boolean;
  title: string;
  body?: string;
  level: NotificationLevel;
}

export interface BackupExportRequest {
  tables?: string[] | null;
}
export interface BackupImportRequest {
  mode: "merge" | "overwrite";
  tables: Record<string, unknown[]>;
}

/* ── AI 세션/트레이스 (추가기능 02, §4.2·§7) ── */
export type AiRole = "designer" | "writer" | "editor" | "chat";
export type AiSessionStatus = "running" | "awaiting_user" | "done" | "error";

/** GET /ai/sessions 의 세션 항목 (06 확장 필드 optional) */
export interface AiSession {
  id: string;
  bookId: string | null;
  role: AiRole;
  model: string;
  status: AiSessionStatus;
  summary: string | null;
  error: string | null;
  startedAt: string;
  endedAt: string | null;
  /* 06 확장 */
  userEmail?: string | null;
  stepCount?: number;
  tokensIn?: number;
  tokensOut?: number;
}

/** ReAct 스텝(트레이스 타임라인 1행) */
export interface AiStep {
  idx: number;
  thought: string;
  skill: string;
  /** 스킬 입력(JSON) */
  args: unknown;
  /** 스킬 결과(JSON) */
  observation: unknown;
  tokensIn: number;
  tokensOut: number;
  ms: number;
  createdAt: string;
}

/** GET /ai/sessions/{id} 응답 = 세션 + 스텝 */
export interface AiSessionDetail extends AiSession {
  steps: AiStep[];
}

/** GET /health 응답 (백엔드 모드 배지용) */
export interface Health {
  status: string;
  version: string;
  env: string;
  /** "supabase" | "memory" 등 */
  storage: string;
  /** "google" | "mock" 등 */
  ai: string;
}

/** 공통 에러 규약 (§4.1) */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    detail?: Record<string, unknown>;
  };
}

/* ── SSE 이벤트 (§5) ── */
export interface SSEMeta {
  chapterIdx: number;
  mode: ChapterMode;
  totalChaptersPlanned: number;
}
export interface SSEIllustration {
  url: string;
  alt: string;
}
export interface SSEPrompt {
  text: string;
}
export interface SSEToken {
  text: string;
}
export interface SSEDone {
  chapterIdx: number;
  words: string[];
  nextChapterAvailable: boolean;
  charCount: number;
}
export interface SSEError {
  code: string;
  message: string;
  retryable: boolean;
}

export type SSEEvent =
  | { type: "meta"; data: SSEMeta }
  | { type: "illustration"; data: SSEIllustration }
  | { type: "prompt"; data: SSEPrompt }
  | { type: "token"; data: SSEToken }
  | { type: "ask"; data: Ask }
  | { type: "done"; data: SSEDone }
  | { type: "error"; data: SSEError };
