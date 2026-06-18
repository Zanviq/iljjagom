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
  AdminMessage,
  AdminSettingsResponse,
  AdminUsage,
  AdminUser,
  AdminUserPatch,
  AiRole,
  AiSession,
  AiSessionDetail,
  AiSessionStatus,
  AppNotification,
  BackupImportRequest,
  Book,
  BoardPost,
  BoardPostCreated,
  BoardPostsResponse,
  BoardPostStatus,
  BookCreated,
  BookSummary,
  ClassSummary,
  CollabReply,
  CollabState,
  CreatePromptRequest,
  Dashboard,
  DesignStatus,
  Health,
  Learning,
  LearningResult,
  LearningResultCreate,
  Letter,
  LetterReply,
  Me,
  NotificationCreate,
  OnboardingRequest,
  PlanReply,
  Prompt,
  SafetyFlag,
  SafetyFlagDetail,
  SafetyFlagStatus,
  SettingPut,
  TokenUsageReport,
  TrackEvent,
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

/** 자유집필 협업 상태 복원(좌 문단·우 대화). 04 기능개선 학생/15. */
export function getCollab(
  token: string | null,
  bookId: string,
  chapterIdx: number,
): Promise<CollabState> {
  return apiFetch<CollabState>(
    `/books/${bookId}/chapters/${chapterIdx}/collab`,
    { token },
  );
}

/** 협업 한 턴: 학생 한 마디 → 한 문단 생성 또는 지도(accept=직전 지도 수용). */
export function postCollab(
  token: string | null,
  bookId: string,
  chapterIdx: number,
  message: string,
  accept?: boolean,
): Promise<CollabReply> {
  return apiFetch<CollabReply>(
    `/books/${bookId}/chapters/${chapterIdx}/collab`,
    {
      token,
      method: "POST",
      body: accept === undefined ? { message } : { message, accept },
    },
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

/** AI 세션 목록(관측, §4.2). admin만. 최근순. (06: role/userId/from/to 필터) */
export function getAiSessions(
  token: string | null,
  params?: {
    bookId?: string;
    status?: AiSessionStatus;
    role?: AiRole;
    userId?: string;
    from?: string;
    to?: string;
    limit?: number;
  },
): Promise<{ sessions: AiSession[] }> {
  const q = new URLSearchParams();
  if (params?.bookId) q.set("bookId", params.bookId);
  if (params?.status) q.set("status", params.status);
  if (params?.role) q.set("role", params.role);
  if (params?.userId) q.set("userId", params.userId);
  if (params?.from) q.set("from", params.from);
  if (params?.to) q.set("to", params.to);
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

/* ── 측정·학습결과 (추가기능 04, §4.2) ── */

/** 행동 로그 배치 수집(student/admin). 1~50개. studentId는 토큰에서. */
export function postEvents(
  token: string | null,
  events: TrackEvent[],
): Promise<{ accepted: number }> {
  return apiFetch<{ accepted: number }>("/events", {
    token,
    method: "POST",
    body: { events },
  });
}

/** 학습 결과 저장(책 소유 학생/admin). type∈quiz|essay|emotion. */
export function postLearningResult(
  token: string | null,
  bookId: string,
  body: LearningResultCreate,
): Promise<{ id: string; type: string; createdAt: string }> {
  return apiFetch<{ id: string; type: string; createdAt: string }>(
    `/books/${bookId}/learning-results`,
    { token, method: "POST", body },
  );
}

/** 학습 결과 조회(책 접근 가능자). */
export function getLearningResults(
  token: string | null,
  bookId: string,
): Promise<{ results: LearningResult[] }> {
  return apiFetch<{ results: LearningResult[] }>(
    `/books/${bookId}/learning-results`,
    { token },
  );
}

/* ── 학급 게시판/발표 (04 기능개선 학생/15·14) ── */

/** 완성 책을 학급 게시판에 발표 등록(책 status=="done"). */
export function postBoardPost(
  token: string | null,
  bookId: string,
  intro?: string,
): Promise<BoardPostCreated> {
  return apiFetch<BoardPostCreated>(`/books/${bookId}/board-posts`, {
    token,
    method: "POST",
    body: intro ? { intro } : {},
  });
}

/** 학급 게시판 목록(학생=published, 교사=전체). */
export function getBoardPosts(
  token: string | null,
  classId: string,
  status?: BoardPostStatus,
): Promise<BoardPostsResponse> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch<BoardPostsResponse>(`/classes/${classId}/board-posts${q}`, {
    token,
  });
}

/** 발표 상세(스냅샷 전체). */
export function getBoardPost(
  token: string | null,
  postId: string,
): Promise<BoardPost> {
  return apiFetch<BoardPost>(`/board-posts/${postId}`, { token });
}

/** 발표 승인(교사). */
export function approveBoardPost(
  token: string | null,
  postId: string,
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/board-posts/${postId}/approve`, {
    token,
    method: "POST",
  });
}

/** 발표 반려(교사). */
export function rejectBoardPost(
  token: string | null,
  postId: string,
  note?: string,
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/board-posts/${postId}/reject`, {
    token,
    method: "POST",
    body: note ? { note } : {},
  });
}

/* ── 관리자 콘솔 (추가기능 06, §4.2) — 전부 admin ── */

export function getAdminUsers(
  token: string | null,
  params?: { query?: string; role?: string; classId?: string },
): Promise<{ users: AdminUser[] }> {
  const q = new URLSearchParams();
  if (params?.query) q.set("query", params.query);
  if (params?.role) q.set("role", params.role);
  if (params?.classId) q.set("classId", params.classId);
  const qs = q.toString();
  return apiFetch<{ users: AdminUser[] }>(`/admin/users${qs ? `?${qs}` : ""}`, {
    token,
  });
}

export function patchAdminUser(
  token: string | null,
  id: string,
  patch: AdminUserPatch,
): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/admin/users/${id}`, {
    token,
    method: "PATCH",
    body: patch,
  });
}

export function deactivateAdminUser(
  token: string | null,
  id: string,
): Promise<{ id: string; status: string }> {
  return apiFetch<{ id: string; status: string }>(
    `/admin/users/${id}/deactivate`,
    { token, method: "POST" },
  );
}

export function getAdminMessages(
  token: string | null,
  params?: {
    userId?: string;
    bookId?: string;
    kind?: string;
    from?: string;
    to?: string;
    limit?: number;
  },
): Promise<{ messages: AdminMessage[] }> {
  const q = new URLSearchParams();
  if (params?.userId) q.set("userId", params.userId);
  if (params?.bookId) q.set("bookId", params.bookId);
  if (params?.kind) q.set("kind", params.kind);
  if (params?.from) q.set("from", params.from);
  if (params?.to) q.set("to", params.to);
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return apiFetch<{ messages: AdminMessage[] }>(
    `/admin/messages${qs ? `?${qs}` : ""}`,
    { token },
  );
}

export function getTokenUsage(
  token: string | null,
  groupBy: "model" | "role" | "day" = "model",
  range?: { from?: string; to?: string },
): Promise<TokenUsageReport> {
  const q = new URLSearchParams({ groupBy });
  if (range?.from) q.set("from", range.from);
  if (range?.to) q.set("to", range.to);
  return apiFetch<TokenUsageReport>(`/admin/usage/tokens?${q.toString()}`, {
    token,
  });
}

export function getAdminSettings(
  token: string | null,
): Promise<AdminSettingsResponse> {
  return apiFetch<AdminSettingsResponse>("/admin/settings", { token });
}

export function putAdminSettings(
  token: string | null,
  body: SettingPut,
): Promise<AdminSettingsResponse> {
  return apiFetch<AdminSettingsResponse>("/admin/settings", {
    token,
    method: "PUT",
    body,
  });
}

export function getAdminNotifications(
  token: string | null,
  params?: { unread?: boolean; limit?: number },
): Promise<{ notifications: AppNotification[] }> {
  const q = new URLSearchParams();
  if (params?.unread) q.set("unread", "true");
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return apiFetch<{ notifications: AppNotification[] }>(
    `/admin/notifications${qs ? `?${qs}` : ""}`,
    { token },
  );
}

export function createNotification(
  token: string | null,
  body: NotificationCreate,
): Promise<AppNotification> {
  return apiFetch<AppNotification>("/admin/notifications", {
    token,
    method: "POST",
    body,
  });
}

export function markNotificationRead(
  token: string | null,
  id: string,
): Promise<{ id: string; readAt: string }> {
  return apiFetch<{ id: string; readAt: string }>(
    `/notifications/${id}/read`,
    { token, method: "POST" },
  );
}

export function backupExport(
  token: string | null,
  tables?: string[] | null,
): Promise<{ exportedAt: string; tables: Record<string, unknown[]> }> {
  return apiFetch<{ exportedAt: string; tables: Record<string, unknown[]> }>(
    "/admin/backup/export",
    { token, method: "POST", body: { tables: tables ?? null } },
  );
}

export function backupImport(
  token: string | null,
  body: BackupImportRequest,
): Promise<{ imported: Record<string, number> }> {
  return apiFetch<{ imported: Record<string, number> }>(
    "/admin/backup/import",
    { token, method: "POST", body },
  );
}
