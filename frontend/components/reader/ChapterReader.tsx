"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { buttonClass } from "@/components/ui/Button";
import { WordPopover } from "@/components/reader/WordPopover";
import { ApiError, getWord } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import { streamChapter } from "@/lib/sse";
import type { SSEDone, SSEIllustration, Word } from "@/lib/types";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const MAX_RECONNECT = 5;

interface Props {
  bookId: string;
  title: string | null;
  totalChaptersPlanned: number;
}

export function ChapterReader({ bookId, title, totalChaptersPlanned }: Props) {
  const [token, setToken] = useState<string | null | undefined>(undefined);
  const [chapterIdx, setChapterIdx] = useState(1);

  const [text, setText] = useState("");
  const [illustration, setIllustration] = useState<SSEIllustration | null>(null);
  const [activePrompt, setActivePrompt] = useState<string | null>(null);
  const [done, setDone] = useState<SSEDone | null>(null);
  const [streaming, setStreaming] = useState(true);
  const [streamError, setStreamError] = useState<string | null>(null);

  // 단어 도움
  const [word, setWord] = useState<Word | null>(null);
  const [wordLoading, setWordLoading] = useState(false);

  const doneRef = useRef(false);

  useEffect(() => {
    getClientAccessToken().then(setToken);
  }, []);

  useEffect(() => {
    if (token === undefined) return;

    const controller = new AbortController();
    let cancelled = false;
    let offset = 0;

    doneRef.current = false;
    setText("");
    setIllustration(null);
    setActivePrompt(null);
    setDone(null);
    setStreamError(null);
    setStreaming(true);

    async function run() {
      let attempts = 0;
      while (!cancelled && attempts <= MAX_RECONNECT) {
        let sawRetryable = false;
        try {
          await streamChapter({
            token: token ?? null,
            bookId,
            chapterIdx,
            fromOffset: offset,
            signal: controller.signal,
            onEvent: (evt) => {
              switch (evt.type) {
                case "illustration":
                  setIllustration(evt.data);
                  break;
                case "prompt":
                  setActivePrompt(evt.data.text);
                  break;
                case "token":
                  offset += evt.data.text.length;
                  setText((t) => t + evt.data.text);
                  break;
                case "done":
                  doneRef.current = true;
                  setDone(evt.data);
                  setStreaming(false);
                  break;
                case "error":
                  if (evt.data.retryable) sawRetryable = true;
                  else {
                    setStreamError(evt.data.message);
                    setStreaming(false);
                    doneRef.current = true; // 더 시도하지 않음
                  }
                  break;
                default:
                  break;
              }
            },
          });
        } catch {
          if (!cancelled) sawRetryable = true; // 네트워크 끊김 → 재연결
        }

        if (cancelled || doneRef.current) return;
        if (sawRetryable) {
          attempts++;
          await sleep(1000);
          continue; // offset 부터 이어받기
        }
        return; // done 없이 정상 종료
      }
      if (!cancelled && !doneRef.current) {
        setStreaming(false);
        setStreamError("연결이 자꾸 끊겨요. 잠시 후 다시 시도해 주세요.");
      }
    }

    void run();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [token, bookId, chapterIdx]);

  const lookUp = useCallback(
    async (term: string) => {
      const clean = term.trim();
      if (!clean || clean.length > 20 || /\s/.test(clean)) return;
      setWordLoading(true);
      setWord(null);
      try {
        const w = await getWord(token ?? null, bookId, clean);
        setWord(w);
      } catch (e) {
        setWord({
          term: clean,
          reading: clean,
          meaning:
            e instanceof ApiError ? e.message : "뜻을 찾지 못했어요.",
        });
      } finally {
        setWordLoading(false);
      }
    },
    [token, bookId],
  );

  function onTextMouseUp() {
    const sel = window.getSelection()?.toString() ?? "";
    if (sel) void lookUp(sel);
  }

  const canGoNext = done?.nextChapterAvailable ?? false;

  return (
    <section className="mx-auto max-w-2xl">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-extrabold">{title || "내 이야기"}</h1>
        <span className="rounded-full bg-accent/40 px-3 py-1 text-sm font-bold">
          {chapterIdx}
          {totalChaptersPlanned ? ` / ${totalChaptersPlanned}` : ""} 장
        </span>
      </div>

      {/* 유도모드: 삽화 선노출 + 능동 질문 (P2 이벤트, 오면 표시) */}
      {illustration && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={illustration.url}
          alt={illustration.alt}
          className="mb-4 w-full rounded-card ring-1 ring-border"
        />
      )}
      {activePrompt && (
        <p className="mb-4 rounded-card bg-secondary/15 p-4 text-lg font-bold text-secondary">
          💬 {activePrompt}
        </p>
      )}

      <article
        onMouseUp={onTextMouseUp}
        className="rounded-card bg-surface p-6 text-xl leading-loose ring-1 ring-border"
      >
        <span className="whitespace-pre-wrap">{text}</span>
        {streaming && <span className="streaming-cursor" aria-hidden />}
        {!text && streaming && (
          <span className="text-muted">이야기를 펼치는 중이에요…</span>
        )}
      </article>

      <p className="mt-2 text-center text-sm text-muted">
        모르는 낱말을 <strong>손가락으로 살짝 선택</strong>하면 뜻을 알려줘요.
      </p>

      {streamError && (
        <p className="mt-4 text-center font-bold text-danger">{streamError}</p>
      )}

      {done && (
        <div className="mt-6 rounded-card bg-surface p-5 ring-1 ring-border">
          {done.words.length > 0 && (
            <>
              <h2 className="text-sm font-bold text-muted">이 장의 낱말</h2>
              <ul className="mt-2 flex flex-wrap gap-2">
                {done.words.map((w) => (
                  <li key={w}>
                    <button
                      onClick={() => void lookUp(w)}
                      className="rounded-full bg-accent/40 px-3 py-1 text-sm font-bold hover:brightness-105"
                    >
                      {w}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
          {canGoNext && (
            <button
              onClick={() => setChapterIdx((i) => i + 1)}
              className={buttonClass("primary", "lg", "mt-4 w-full")}
            >
              다음 장으로 →
            </button>
          )}
          {!canGoNext && (
            <p className="mt-2 text-center font-bold text-success">
              🎉 이야기를 모두 읽었어요!
            </p>
          )}
        </div>
      )}

      {(word || wordLoading) && (
        <WordPopover
          word={word}
          loading={wordLoading}
          onClose={() => setWord(null)}
        />
      )}
    </section>
  );
}
