"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { buttonClass } from "@/components/ui/Button";
import { WordPopover } from "@/components/reader/WordPopover";
import { ApiError, getBook, getWord, reviseChapter } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import { streamChapter } from "@/lib/sse";
import type { ChapterMode, SSEDone, SSEIllustration, Word } from "@/lib/types";

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
  // 수정요청(revise) 완료 시 값을 바꿔 ChapterStream을 재마운트 → 저장본(수정 반영) 재구독.
  const [reloadNonce, setReloadNonce] = useState(0);

  useEffect(() => {
    getClientAccessToken().then(setToken);
  }, []);

  return (
    <section className="mx-auto max-w-2xl">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-extrabold">{title || "내 이야기"}</h1>
        <span className="rounded-full bg-accent/40 px-3 py-1 text-sm font-bold">
          {chapterIdx}
          {totalChaptersPlanned ? ` / ${totalChaptersPlanned}` : ""} 장
        </span>
      </div>

      {token === undefined ? (
        <p className="rounded-card bg-surface p-6 text-muted ring-1 ring-border">
          이야기를 준비하는 중이에요…
        </p>
      ) : (
        // 챕터 변경 또는 수정요청 완료 시 key 변경으로 스트림을 새로 마운트(상태 초기화·재구독).
        <ChapterStream
          key={`${chapterIdx}-${reloadNonce}`}
          token={token}
          bookId={bookId}
          chapterIdx={chapterIdx}
          totalChaptersPlanned={totalChaptersPlanned}
          onNext={() => setChapterIdx((i) => i + 1)}
          onRevised={() => setReloadNonce((n) => n + 1)}
          onRetry={() => setReloadNonce((n) => n + 1)}
        />
      )}
    </section>
  );
}

function ChapterStream({
  token,
  bookId,
  chapterIdx,
  totalChaptersPlanned,
  onNext,
  onRevised,
  onRetry,
}: {
  token: string | null;
  bookId: string;
  chapterIdx: number;
  totalChaptersPlanned: number;
  onNext: () => void;
  onRevised: () => void;
  onRetry: () => void;
}) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState<ChapterMode | null>(null);
  const [illustration, setIllustration] = useState<SSEIllustration | null>(null);
  const [activePrompt, setActivePrompt] = useState<string | null>(null);
  const [done, setDone] = useState<SSEDone | null>(null);
  const [streaming, setStreaming] = useState(true);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [word, setWord] = useState<Word | null>(null);
  const [wordLoading, setWordLoading] = useState(false);
  // 유도(guided) 모드: 삽화+능동 질문을 먼저 보여주고, 아이가 탭하면 본문을 공개한다.
  // 자유(free) 모드: 본문을 곧바로 공개(meta 수신 시 true). meta 수신 전 기본값은 false.
  const [revealed, setRevealed] = useState(false);
  // 자유모드 수정요청(revise) 상태.
  const [reviseOpen, setReviseOpen] = useState(false);
  const [reviseText, setReviseText] = useState("");
  const [revising, setRevising] = useState(false);
  const [reviseError, setReviseError] = useState<string | null>(null);

  const doneRef = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    let offset = 0;

    async function run() {
      let attempts = 0;
      while (!cancelled && attempts <= MAX_RECONNECT) {
        let sawRetryable = false;
        try {
          await streamChapter({
            token,
            bookId,
            chapterIdx,
            fromOffset: offset,
            signal: controller.signal,
            onEvent: (evt) => {
              switch (evt.type) {
                case "meta":
                  setMode(evt.data.mode);
                  // 자유 모드는 본문 바로 공개. 유도 모드는 탭 전까지 숨김.
                  if (evt.data.mode === "free") setRevealed(true);
                  break;
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
                    doneRef.current = true;
                  }
                  break;
                default:
                  break;
              }
            },
          });
        } catch {
          if (!cancelled) sawRetryable = true;
        }

        if (cancelled || doneRef.current) return;
        if (sawRetryable) {
          attempts++;
          await sleep(1000);
          continue;
        }
        return;
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
        const w = await getWord(token, bookId, clean);
        setWord(w);
      } catch (e) {
        setWord({
          term: clean,
          reading: clean,
          meaning: e instanceof ApiError ? e.message : "뜻을 찾지 못했어요.",
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

  // 수정요청: revise 호출 → reviewStatus 가 ok 로 돌아올 때까지 폴링 → 재구독(저장본=수정본).
  async function submitRevise() {
    const instruction = reviseText.trim();
    if (!instruction || revising) return;
    setRevising(true);
    setReviseError(null);
    try {
      await reviseChapter(token, bookId, chapterIdx, instruction);
    } catch (e) {
      setRevising(false);
      setReviseError(
        e instanceof ApiError ? e.message : "수정 요청을 보내지 못했어요.",
      );
      return;
    }
    // 비동기 처리(해석→재생성→Tier3 편집→반영) 완료 대기: reviewStatus revising→ok.
    // 실 AI는 3단계 LLM 호출이라 오래 걸릴 수 있어 넉넉히(약 3분) 폴링한다.
    // 시작 직후 잠깐의 ok(직전 상태)를 완료로 오인하지 않도록, "revising"을 한 번 본 뒤의
    // ok(또는 충분한 시간 경과 후의 ok)만 완료로 인정한다.
    let sawRevising = false;
    for (let i = 0; i < 90; i++) {
      await sleep(2000);
      try {
        const book = await getBook(token, bookId);
        const ch = book.chapters.find((c) => c.idx === chapterIdx);
        if (!ch) continue;
        if (ch.reviewStatus === "revising") {
          sawRevising = true;
          continue;
        }
        if (ch.reviewStatus === "ok" && (sawRevising || i >= 3)) {
          onRevised(); // 부모가 key 변경 → 재마운트 → 수정 반영된 저장본 재구독
          return;
        }
      } catch {
        // 일시 오류는 무시하고 계속 폴링
      }
    }
    setRevising(false);
    setReviseError(
      "수정이 아직 진행 중이에요. 잠시 후 새로고침하면 반영돼요.",
    );
  }

  const canGoNext = done?.nextChapterAvailable ?? false;
  // 마지막 장(=완독) 여부. 계획된 장 수를 알 때만 판단.
  const isLastChapter =
    totalChaptersPlanned > 0 && chapterIdx >= totalChaptersPlanned;
  // 유도 모드에서 아직 본문을 공개하지 않은 상태(삽화·질문 먼저 보는 단계).
  const guidedGate = mode === "guided" && !revealed;

  return (
    <>
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

      {/* 유도 모드: 삽화·질문을 먼저 보고, 탭하면 본문을 공개한다. */}
      {guidedGate && (
        <div className="rounded-card bg-surface p-6 text-center ring-1 ring-border">
          {illustration || activePrompt ? (
            <>
              <p className="mb-4 text-lg font-bold">
                그림을 보고 어떤 이야기일지 상상해 봐요.
              </p>
              <button
                onClick={() => setRevealed(true)}
                className={buttonClass("primary", "lg", "w-full")}
              >
                ▶ 이야기 읽어볼까요?
              </button>
            </>
          ) : (
            <>
              <div
                className="mb-4 aspect-video w-full animate-pulse rounded-card bg-accent/30"
                aria-hidden
              />
              <p className="text-muted">그림을 준비하는 중이에요…</p>
            </>
          )}
        </div>
      )}

      {/* meta 수신 전(모드 미확정) 잠깐의 로딩 */}
      {mode === null && !revealed && (
        <p className="rounded-card bg-surface p-6 text-muted ring-1 ring-border">
          이야기를 준비하는 중이에요…
        </p>
      )}

      {revealed && (
        <>
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
        </>
      )}

      {streamError && (
        <p className="mt-4 text-center font-bold text-danger">{streamError}</p>
      )}

      {revealed && done && (
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
          {canGoNext ? (
            <button
              onClick={onNext}
              className={buttonClass("primary", "lg", "mt-4 w-full")}
            >
              다음 장으로 →
            </button>
          ) : isLastChapter ? (
            // 마지막 장 완독: 축하 + 학습활동 진입.
            <div className="mt-2 text-center">
              <p className="text-lg font-bold text-success">
                🎉 이야기를 모두 읽었어요!
              </p>
              <Link
                href={`/books/${bookId}/learn`}
                className={buttonClass("primary", "lg", "mt-4 w-full")}
              >
                📚 학습 활동 하러 가기
              </Link>
            </div>
          ) : (
            // 아직 마지막 장이 아닌데 다음 장이 준비되지 않음(생성 중/검수 대기).
            // 거짓 완독으로 오인하지 않도록 안내 + 다시 확인.
            <div className="mt-2 text-center">
              <p className="font-bold text-muted">
                다음 장을 준비하고 있어요. 잠시 후 다시 확인해 주세요.
              </p>
              <button
                onClick={onRetry}
                className={buttonClass("outline", "md", "mt-3 w-full")}
              >
                ↻ 다시 확인할래요
              </button>
            </div>
          )}
        </div>
      )}

      {/* 자유모드 수정요청: 다 쓰인 자유 챕터에서 본문을 고쳐 달라고 요청. */}
      {revealed && done && mode === "free" && (
        <div className="mt-4 rounded-card bg-surface p-5 ring-1 ring-border">
          {revising ? (
            <p className="text-center font-bold text-secondary">
              <span className="streaming-cursor" aria-hidden /> 이야기를 고치고
              있어요… 잠시만 기다려 주세요.
            </p>
          ) : reviseOpen ? (
            <>
              <label className="flex flex-col gap-2">
                <span className="font-bold">어떻게 고칠까요?</span>
                <textarea
                  value={reviseText}
                  onChange={(e) => setReviseText(e.target.value)}
                  rows={3}
                  placeholder="예) 주인공을 더 씩씩하게 바꿔 줘"
                  className="rounded-xl border-2 border-border bg-background p-3 text-lg"
                />
              </label>
              {reviseError && (
                <p className="mt-2 text-sm font-bold text-danger">
                  {reviseError}
                </p>
              )}
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => void submitRevise()}
                  disabled={!reviseText.trim()}
                  className={buttonClass("primary", "md", "flex-1")}
                >
                  고쳐 주세요
                </button>
                <button
                  onClick={() => {
                    setReviseOpen(false);
                    setReviseError(null);
                  }}
                  className={buttonClass("ghost", "md")}
                >
                  취소
                </button>
              </div>
            </>
          ) : (
            <button
              onClick={() => setReviseOpen(true)}
              className={buttonClass("outline", "md", "w-full")}
            >
              ✏️ 이야기 고치기
            </button>
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
    </>
  );
}
