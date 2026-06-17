/**
 * AI 세션(ReAct) 관련 프론트 타입·호출.
 * 정본 계약(03-기능명세서 §4/§7)에 admin/ai-session API가 확정되면 이 파일을 그에 맞춘다.
 * - ask_user: AI가 흐름 도중 사용자에게 질문하고 응답을 받아 재개하는 메커니즘(02 문서 §4.2).
 *   질문 노출 경로(SSE `ask` vs 폴링)는 백엔드 확정 대기(handoff requests.md OPEN).
 *   그러나 응답 엔드포인트 `POST /ai/sessions/{id}/answer {choice?, text?}` 형태는 02 문서에 명시됨.
 */
import { apiFetch } from "./api";

/** ask_user 스킬이 제시하는 질문(클로드식 질문칸). */
export interface AskUserPrompt {
  /** 응답을 보낼 AI 세션 id */
  sessionId: string;
  /** 아이에게 보여줄 질문 */
  question: string;
  /** 선택지(없으면 직접 입력만). */
  choices: string[];
  /** 선택지 외 자유 입력 허용 여부 */
  allowText: boolean;
}

/** ask_user 응답 본문. choice(선택지 index) 또는 text(직접 입력) 중 하나. */
export interface AskUserAnswer {
  choice?: number;
  text?: string;
}

/**
 * ask_user 응답 전송 → AI 흐름 재개 (02 §4.2).
 * 백엔드 미구현이면 ApiError(404)로 떨어지므로 호출부에서 graceful 처리.
 */
export function answerAiSession(
  token: string | null,
  sessionId: string,
  answer: AskUserAnswer,
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/ai/sessions/${sessionId}/answer`, {
    token,
    method: "POST",
    body: answer,
  });
}
