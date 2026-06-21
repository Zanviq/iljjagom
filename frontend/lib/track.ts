/**
 * 행동 로그 수집 클라이언트(추가기능 04). 이벤트를 모아 배치로 `POST /events`.
 * - flush 트리거: 5개 누적 / 10초 타이머 / 페이지 이탈(visibilitychange hidden·pagehide).
 * - 이탈 시점은 keepalive fetch 로 보낸다(sendBeacon 은 Authorization 헤더를 못 실어 401).
 * - **측정 실패는 학습 흐름을 절대 막지 않는다**(조용히 무시, 손실 허용).
 */
import { API_BASE_URL, postEvents } from "./api";
import { getClientAccessToken } from "./auth/client";
import type { EventType, TrackEvent } from "./types";

const FLUSH_MS = 10_000;
const MAX_BATCH = 5; // 이만큼 쌓이면 즉시 flush
const FLUSH_LIMIT = 50; // 한 번의 flush 에서 보낼 최대 이벤트 수(폭주 방지)

const queue: TrackEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let listenersAdded = false;

function ensureListeners() {
  if (listenersAdded || typeof document === "undefined") return;
  listenersAdded = true;
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") void flush(true);
  });
  window.addEventListener("pagehide", () => void flush(true));
}

/** 이벤트 1건 큐에 적재. SSR/비브라우저에서는 무시. */
export function track(
  type: EventType,
  opts?: { bookId?: string | null; payload?: Record<string, unknown> },
) {
  if (typeof window === "undefined") return;
  ensureListeners();
  queue.push({
    type,
    bookId: opts?.bookId ?? null,
    payload: opts?.payload,
    clientTs: new Date().toISOString(),
  });
  if (queue.length >= MAX_BATCH) {
    void flush();
    return;
  }
  if (!timer) timer = setTimeout(() => void flush(), FLUSH_MS);
}

/** 큐를 비우고 전송. beacon=true 면 이탈 중에도 도달하도록 keepalive 사용. */
export async function flush(beacon = false) {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  if (queue.length === 0) return;
  // 토큰을 먼저 확보한 뒤 큐를 비운다. 토큰 조회가 실패하면 이벤트를 떼지 않아
  // 다음 flush 에서 재시도된다(전송 자체 실패는 설계상 손실 허용).
  let token: string | null;
  try {
    token = await getClientAccessToken();
  } catch {
    return;
  }
  const batch = queue.splice(0, FLUSH_LIMIT);
  try {
    if (beacon) {
      await fetch(`${API_BASE_URL}/events`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ events: batch }),
        keepalive: true,
      });
    } else {
      await postEvents(token, batch);
    }
  } catch {
    // 측정 실패는 학습 흐름을 막지 않는다(조용히 무시, 재시도 없음).
  }
}
