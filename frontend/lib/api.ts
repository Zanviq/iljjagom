/**
 * 백엔드(FastAPI) REST 호출 래퍼. 03-기능명세서 §4 계약을 그대로 호출한다.
 * - 인증: `Authorization: Bearer <token>` (Supabase access_token 또는 개발 토큰 dev:email:role).
 * - 에러: §4.1 공통 규약 `{error:{code,message,detail}}` → ApiError 로 던진다.
 * - 토큰을 인자로 받아 서버/클라이언트 양쪽에서 동일 경로로 호출(토큰 출처만 다름).
 *
 * 백엔드가 외부 키 없이 인메모리·mock로 P1 계약을 그대로 제공하므로, 프론트는 별도 목업 없이
 * 항상 이 실제 호출 경로를 쓴다(키 생기면 백엔드만 실 DB/AI로 전환).
 */
import type {
  AdminUsage,
  AiSession,
  AiSessionDetail,
  AiSessionStatus,
  Book,
  BookCreated,
  BookSummary,
  ClassSummary,
  CreatePromptRequest,
  Dashboard,
  DesignStatus,
  Health,
  Learning,
  Letter,
  LetterReply,
  Me,
  OnboardingRequest,
  PlanReply,
  Prompt,
  SafetyFlag,
  SafetyFlagDetail,
  SafetyFlagStatus,
  Word,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  status: number;
  detail?: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    detail?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  token?: string | null;
  body?: unknown;
}

export async function apiFetch<T>(
  path: string,
  { token, body, headers, ...init }: ApiFetchOptions = {},
): Promise<T> {
  const finalHeaders = new Headers(headers);
  if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  if (body !== undefined && !finalHeaders.has("Content-Type")) {
    finalHeaders.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: finalHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "백엔드에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.",
    );
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const payload = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const err = payload?.error ?? {};
    throw new ApiError(
      res.status,
      err.code ?? "internal_error",
      err.message ?? "알 수 없는 오류가 발생했어요.",
      err.detail,
    );
  }

  return payload as T;
}

/* ── 엔드포인트 (§4.2) ── 토큰을 받아 호출. 서버/클라이언트 공용. ── */

export function getMe(token: string | null): Promise<Me> {
  return apiFetch<Me>("/me", { token });
}

export function postOnboarding(
  token: string | null,
  body: OnboardingRequest,
): Promise<Me> {
  return apiFetch<Me>("/onboarding", { token, method: "POST", body });
}

export function getClasses(
  token: string | null,
): Promise<{ classes: ClassSummary[] }> {
  return apiFetch<{ classes: ClassSummary[] }>("/classes", { token });
}

export function getPrompts(
  token: string | null,
  classId: string,
): Promise<{ prompts: Prompt[] }> {
  return apiFetch<{ prompts: Prompt[] }>(`/classes/${classId}/prompts`, {
    token,
  });
}

export function createPrompt(
  token: string | null,
  classId: string,
  body: CreatePromptRequest,
): Promise<Prompt> {
  return apiFetch<Prompt>(`/classes/${classId}/prompts`, {
    token,
    method: "POST",
    body,
  });
}

export function getBooks(
  token: string | null,
): Promise<{ books: BookSummary[] }> {
  return apiFetch<{ books: BookSummary[] }>("/books", { token });
}

export function createBook(
  token: string | null,
  promptId: string,
): Promise<BookCreated> {
  return apiFetch<BookCreated>("/books", {
    token,
    method: "POST",
    body: { promptId },
  });
}

export function getBook(token: string | null, bookId: string): Promise<Book> {
  return apiFetch<Book>(`/books/${bookId}`, { token });
}

export function postPlanMessage(
  token: string | null,
  bookId: string,
  message: string,
): Promise<PlanReply> {
  return apiFetch<PlanReply>(`/books/${bookId}/plan/messages`, {
    token,
    method: "POST",
    body: { message },
  });
}

export function postDesign(
  token: string | null,
  bookId: string,
): Promise<DesignStatus> {
  return apiFetch<DesignStatus>(`/books/${bookId}/design`, {
    token,
    method: "POST",
  });
}

/** 자유모드 수정요청 (FR-S6). 202 {status:"revising"}. 완료는 stream 재구독 + reviewStatus 폴링. */
export function reviseChapter(
  token: string | null,
  bookId: string,
  chapterIdx: number,
  instruction: string,
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(
    `/books/${bookId}/chapters/${chapterIdx}/revise`,
    { token, method: "POST", body: { instruction } },
  );
}

export function getWord(
  token: string | null,
  bookId: string,
  term: string,
): Promise<Word> {
  return apiFetch<Word>(
    `/books/${bookId}/words?term=${encodeURIComponent(term)}`,
    { token },
  );
}

/** 교사 대시보드 (FR-T2). 담당 교사/admin만. */
export function getDashboard(
  token: string | null,
  classId: string,
): Promise<Dashboard> {
  return apiFetch<Dashboard>(`/classes/${classId}/dashboard`, { token });
}

/** 학습 활동 (FR-S8~S12). 책 접근 가능자. */
export function getLearning(
  token: string | null,
  bookId: string,
): Promise<Learning> {
  return apiFetch<Learning>(`/books/${bookId}/learning`, { token });
}

/** 인물 편지 (FR-S11). held=교사 확인 보류. */
export function postLetter(
  token: string | null,
  bookId: string,
  to: string,
  body: string,
): Promise<LetterReply> {
  return apiFetch<LetterReply>(`/books/${bookId}/letters`, {
    token,
    method: "POST",
    body: { to, body },
  });
}

/** 관리자 사용량/안전 신호 (FR-M1). admin만. */
export function getAdminUsage(token: string | null): Promise<AdminUsage> {
  return apiFetch<AdminUsage>("/admin/usage", { token });
}

/** 백엔드 상태/모드(저장소·AI). 인증 불필요. 관리자 콘솔 모드 배지용. */
export function getHealth(): Promise<Health> {
  return apiFetch<Health>("/health");
}

/** AI 세션 목록(관측, §4.2). admin만. 최근순. */
export function getAiSessions(
  token: string | null,
  params?: { bookId?: string; status?: AiSessionStatus; limit?: number },
): Promise<{ sessions: AiSession[] }> {
  const q = new URLSearchParams();
  if (params?.bookId) q.set("bookId", params.bookId);
  if (params?.status) q.set("status", params.status);
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return apiFetch<{ sessions: AiSession[] }>(
    `/ai/sessions${qs ? `?${qs}` : ""}`,
    { token },
  );
}

/** AI 세션 상세 + 스텝 트레이스(§4.2). admin만. */
export function getAiSession(
  token: string | null,
  id: string,
): Promise<AiSessionDetail> {
  return apiFetch<AiSessionDetail>(`/ai/sessions/${id}`, { token });
}

/* ── 안전·교사검토 (추가기능 03, §4.2) ── */

/** 학급 안전 신호 목록(teacher/admin). */
export function getClassSafetyFlags(
  token: string | null,
  classId: string,
  params?: { status?: SafetyFlagStatus; source?: string },
): Promise<{ flags: SafetyFlag[] }> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.source) q.set("source", params.source);
  const qs = q.toString();
  return apiFetch<{ flags: SafetyFlag[] }>(
    `/classes/${classId}/safety-flags${qs ? `?${qs}` : ""}`,
    { token },
  );
}

/** 안전 신호 상세(연결 편지 포함, teacher/admin). */
export function getSafetyFlag(
  token: string | null,
  id: string,
): Promise<SafetyFlagDetail> {
  return apiFetch<SafetyFlagDetail>(`/safety-flags/${id}`, { token });
}

/** 안전 신호 종결(teacher/admin). */
export function resolveSafetyFlag(
  token: string | null,
  id: string,
  note?: string,
): Promise<SafetyFlag> {
  return apiFetch<SafetyFlag>(`/safety-flags/${id}/resolve`, {
    token,
    method: "POST",
    body: { note },
  });
}

/** 전 학급 안전 신호(admin). */
export function getAdminSafetyFlags(
  token: string | null,
  status?: SafetyFlagStatus,
): Promise<{ flags: SafetyFlag[] }> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<{ flags: SafetyFlag[] }>(`/admin/safety-flags${qs}`, {
    token,
  });
}

/** 학급 편지 목록(teacher/admin). */
export function getClassLetters(
  token: string | null,
  classId: string,
  status?: string,
): Promise<{ letters: Letter[] }> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<{ letters: Letter[] }>(
    `/classes/${classId}/letters${qs}`,
    { token },
  );
}

/** 편지 답장 승인(teacher/admin). reply 없고 useAiReply면 AI 페르소나 답장 생성. */
export function approveLetter(
  token: string | null,
  id: string,
  body: { reply?: string; useAiReply?: boolean },
): Promise<Letter> {
  return apiFetch<Letter>(`/letters/${id}/approve`, {
    token,
    method: "POST",
    body,
  });
}

/** 편지 답장 미발송(teacher/admin). */
export function rejectLetter(
  token: string | null,
  id: string,
  note?: string,
): Promise<Letter> {
  return apiFetch<Letter>(`/letters/${id}/reject`, {
    token,
    method: "POST",
    body: { note },
  });
}

/** 학생 본인/교사/admin: 책의 편지 상태·승인된 답장. */
export function getBookLetters(
  token: string | null,
  bookId: string,
): Promise<{ letters: Letter[] }> {
  return apiFetch<{ letters: Letter[] }>(`/books/${bookId}/letters`, { token });
}
