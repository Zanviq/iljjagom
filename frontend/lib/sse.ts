/**
 * 집필 스트림(SSE) 구독 유틸. 03-기능명세서 §5.
 * EventSource 대신 fetch 사용 — Authorization 헤더로 토큰을 전달하기 위해.
 * 이벤트: meta | illustration | prompt | token | ask | done | error. (`: ping` 하트비트는 무시)
 */
import { API_BASE_URL } from "./api";
import type { SSEEvent } from "./types";

const KNOWN_EVENTS = new Set([
  "meta",
  "illustration",
  "prompt",
  "token",
  "ask",
  "done",
  "error",
]);

export interface StreamChapterOptions {
  token: string | null;
  bookId: string;
  chapterIdx: number;
  /** 재연결 시 이어받을 문자 오프셋(?from=). */
  fromOffset?: number;
  signal?: AbortSignal;
  onEvent: (event: SSEEvent) => void;
}

function toEvent(name: string, raw: string): SSEEvent | null {
  if (!KNOWN_EVENTS.has(name)) return null;
  let data: unknown = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    return null;
  }
  // 이벤트명과 data를 그대로 매핑(타입은 §5 계약을 신뢰).
  return { type: name, data } as SSEEvent;
}

/** 한 챕터의 집필 스트림을 구독한다. done/error 또는 스트림 종료 시 resolve. */
export async function streamChapter(opts: StreamChapterOptions): Promise<void> {
  const url = new URL(
    `${API_BASE_URL}/books/${opts.bookId}/chapters/${opts.chapterIdx}/stream`,
  );
  if (opts.fromOffset && opts.fromOffset > 0) {
    url.searchParams.set("from", String(opts.fromOffset));
  }

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
      ...(opts.token ? { Authorization: `Bearer ${opts.token}` } : {}),
    },
    signal: opts.signal,
    cache: "no-store",
  });

  if (!res.ok || !res.body) {
    opts.onEvent({
      type: "error",
      data: {
        code: "internal_error",
        message: "스트림을 시작할 수 없어요.",
        retryable: true,
      },
    });
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // 이벤트는 빈 줄로 구분된다. 프록시/서버가 CRLF(\r\n\r\n)를 쓸 수 있어 둘 다 허용.
    let m: RegExpMatchArray | null;
    while ((m = buffer.match(/\r?\n\r?\n/)) !== null) {
      const sep = m.index!;
      const chunk = buffer.slice(0, sep);
      buffer = buffer.slice(sep + m[0].length);

      let eventName = "message";
      const dataLines: string[] = [];
      for (const line of chunk.split(/\r?\n/)) {
        if (line.startsWith(":")) continue; // 하트비트 코멘트
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }

      const evt = toEvent(eventName, dataLines.join("\n"));
      if (evt) opts.onEvent(evt);
    }
  }
}
