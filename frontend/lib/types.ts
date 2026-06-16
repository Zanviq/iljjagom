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
  | { type: "done"; data: SSEDone }
  | { type: "error"; data: SSEError };
