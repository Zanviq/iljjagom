"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AskUserPanel } from "@/components/ai/AskUserPanel";
import { Button, buttonClass } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ErrorText } from "@/components/ui/ErrorText";
import { Icon } from "@/components/ui/Icon";
import { Loading } from "@/components/ui/Loading";
import { Textarea } from "@/components/ui/Textarea";
import { WordPopover } from "@/components/reader/WordPopover";
import { answerAiSession } from "@/lib/ai";
import type { AskUserAnswer } from "@/lib/ai";
import { ApiError, getBook, getWord, reviseChapter } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import { streamChapter } from "@/lib/sse";
import { track } from "@/lib/track";
import type { Ask, ChapterMode, SSEDone, SSEIllustration, Word } from "@/lib/types";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const MAX_RECONNECT = 8;

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
    <div className="relative mx-auto w-full max-w-[820px] px-6 pb-16 pt-6">
      <div className="mb-[18px] flex items-center justify-between gap-3">
        <Link
          href="/home"
          className="inline-flex items-center gap-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
        >
          <Icon name="arrow-left" size={16} />
          내 책장
        </Link>
        <Badge tone="primary" dot>
          {chapterIdx}
          {totalChaptersPlanned ? ` / ${totalChaptersPlanned}` : ""}장
        </Badge>
      </div>

      <h1
        className="mb-5 text-center"
        style={{
          fontFamily: "var(--font-serif)",
          fontWeight: 600,
          fontSize: 34,
          letterSpacing: "-.02em",
          color: "var(--text-1)",
        }}
      >
        <span
          className="ijg-eyebrow mb-2 block"
          style={{ color: "var(--primary-text)" }}
        >
          {chapterIdx}장
        </span>
        {title || "내 이야기"}
      </h1>

      {token === undefined ? (
        <Loading card>이야기를 준비하는 중이에요…</Loading>
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
    </div>
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
  // 유도 흐름 중 AI 되물음(ask_user). 비차단: 답하지 않아도 읽기는 계속된다.
  const [ask, setAsk] = useState<Ask | null>(null);
  const [answeringAsk, setAnsweringAsk] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
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
  // 체류 측정용: 도달 단계(opened→read→done).
  const reachedRef = useRef<"opened" | "read" | "done">("opened");

  // 본문이 공개되면 체류 도달 단계를 'read'로 올린다(자유=즉시, 유도=탭 후).
  useEffect(() => {
    if (revealed && reachedRef.current === "opened") reachedRef.current = "read";
  }, [revealed]);

  // 챕터 열람/체류 계측(추가기능 04): 마운트 시 chapter_open, 언마운트 시 chapter_dwell.
  useEffect(() => {
    const mountTs = performance.now();
    track("chapter_open", { bookId, payload: { chapterIdx } });
    return () => {
      track("chapter_dwell", {
        bookId,
        payload: {
          chapterIdx,
          ms: Math.round(performance.now() - mountTs),
          reached: reachedRef.current,
        },
      });
    };
  }, [bookId, chapterIdx]);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    let offset = 0;

    async function run() {
      let attempts = 0;
      let waited = 0;
      const MAX_WAIT_MS = 60_000;
      while (!cancelled && attempts <= MAX_RECONNECT) {
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
                case "ask":
                  setAsk(evt.data);
                  break;
                case "token":
                  offset += evt.data.text.length;
                  setText((t) => t + evt.data.text);
                  break;
                case "done":
                  doneRef.current = true;
                  reachedRef.current = "done";
                  setDone(evt.data);
                  setStreaming(false);
                  track("chapter_done", {
                    bookId,
                    payload: {
                      chapterIdx,
                      charCount: evt.data.charCount,
                      nextAvailable: evt.data.nextChapterAvailable,
                    },
                  });
                  if (
                    totalChaptersPlanned > 0 &&
                    chapterIdx >= totalChaptersPlanned
                  ) {
                    track("book_finished", {
                      bookId,
                      payload: { totalChapters: totalChaptersPlanned },
                    });
                  }
                  break;
                case "error":
                  // 재시도 가능 오류는 무시하고 아래 루프가 재구독하게 둔다.
                  if (!evt.data.retryable) {
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
          // 네트워크 단절 등은 아래 재시도 분기에서 처리.
        }

        if (cancelled || doneRef.current) return;
        // done 없이 끝난 정상종료(빈 스트림·프록시 idle 끊김 포함)도 재시도 대상.
        // 지수 백오프 + jitter, 누적 대기 상한으로 무한 로딩/즉시 포기를 모두 막는다.
        attempts++;
        if (waited >= MAX_WAIT_MS) break;
        const delay =
          Math.min(1000 * 2 ** (attempts - 1), 8000) +
          Math.floor(Math.random() * 400);
        waited += delay;
        await sleep(delay);
      }
      if (!cancelled && !doneRef.current) {
        setStreaming(false);
        setStreamError("연결이 잠시 불안정해요. 아래 버튼으로 다시 시도해 주세요.");
      }
    }

    void run();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [token, bookId, chapterIdx, totalChaptersPlanned]);

  const lookUp = useCallback(
    async (term: string) => {
      const clean = term.trim();
      if (!clean || clean.length > 20 || /\s/.test(clean)) return;
      setWordLoading(true);
      setWord(null);
      try {
        const w = await getWord(token, bookId, clean);
        setWord(w);
        track("word_touch", { bookId, payload: { term: clean } });
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
    track("revise_request", { bookId, payload: { chapterIdx } });
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
    setReviseError("수정이 아직 진행 중이에요. 잠시 후 새로고침하면 반영돼요.");
  }

  async function submitAsk(answer: AskUserAnswer) {
    if (!ask || answeringAsk) return;
    setAnsweringAsk(true);
    setAskError(null);
    try {
      await answerAiSession(token, ask.sessionId, answer);
      setAsk(null);
    } catch (e) {
      setAskError(e instanceof ApiError ? e.message : "대답을 전하지 못했어요.");
    } finally {
      setAnsweringAsk(false);
    }
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
        <Illustration
          key={illustration.url}
          url={illustration.url}
          alt={illustration.alt || "이야기 삽화"}
        />
      )}

      {activePrompt && (
        <Card
          tone="accent"
          padding="md"
          className="mb-4"
          style={{ display: "flex", alignItems: "flex-start", gap: 8 }}
        >
          <Icon
            name="message-circle"
            size={20}
            style={{ color: "var(--accent-text)", flex: "none", marginTop: 2 }}
          />
          <p
            className="text-[length:var(--text-md)] font-bold"
            style={{ color: "var(--accent-text)" }}
          >
            {activePrompt}
          </p>
        </Card>
      )}

      {/* AI 되물음(ask_user): 답해도/안 해도 읽기는 계속(비차단). */}
      {ask && (
        <div className="mb-4">
          <AskUserPanel
            prompt={ask}
            pending={answeringAsk}
            error={askError}
            onAnswer={(a) => void submitAsk(a)}
          />
        </div>
      )}

      {/* 유도 모드: 삽화·질문을 먼저 보고, 탭하면 본문을 공개한다. */}
      {guidedGate && (
        <Card tone="primary" padding="lg" className="mt-[22px]" style={{ textAlign: "center" }}>
          {illustration || activePrompt ? (
            <>
              <p
                style={{
                  fontFamily: "var(--font-serif)",
                  fontStyle: "italic",
                  fontSize: 20,
                  color: "var(--text-1)",
                }}
              >
                &ldquo;이건 어떤 장면일까?&rdquo;
              </p>
              <p className="my-2 text-[length:var(--text-sm)] text-ink-2">
                곰 작가가 그림을 먼저 보여 줬어요. 이야기가 궁금하면 열어 봐요.
              </p>
              <Button
                size="lg"
                icon="book-open"
                onClick={() => {
                  setRevealed(true);
                  track("prompt_reveal", { bookId, payload: { chapterIdx } });
                }}
                className="mt-2"
              >
                이야기 읽어볼까요?
              </Button>
            </>
          ) : (
            <>
              <div
                className="mb-4 aspect-video w-full animate-pulse rounded-[var(--radius-card)] bg-accent-tint"
                aria-hidden
              />
              <p className="text-ink-2">그림을 준비하는 중이에요…</p>
            </>
          )}
        </Card>
      )}

      {/* meta 수신 전(모드 미확정) 잠깐의 로딩 */}
      {mode === null && !revealed && (
        <Loading card>이야기를 준비하는 중이에요…</Loading>
      )}

      {revealed && (
        <div className="mt-[26px]">
          <div onMouseUp={onTextMouseUp}>
            <p
              className={streaming ? "ijg-caret" : undefined}
              style={{
                fontFamily: "var(--font-reading)",
                fontSize: "var(--text-read)",
                lineHeight: "var(--leading-read)",
                color: "var(--text-1)",
                maxWidth: "var(--measure-read)",
                margin: "0 auto",
                whiteSpace: "pre-wrap",
              }}
            >
              {text}
              {!text && streaming && (
                <span className="text-ink-3">이야기를 펼치는 중이에요…</span>
              )}
            </p>
          </div>

          <p className="mt-3 text-center text-[length:var(--text-sm)] text-ink-3">
            모르는 낱말을 <strong>손가락으로 살짝 선택</strong>하면 뜻을
            알려줘요.
          </p>
        </div>
      )}

      {streamError && (
        <div className="mt-4 flex flex-col items-center gap-3">
          <ErrorText className="text-center">{streamError}</ErrorText>
          <Button variant="outline" icon="refresh-cw" onClick={onRetry}>
            다시 시도
          </Button>
        </div>
      )}

      {revealed && done && (
        <div className="mt-8">
          {done.words.length > 0 && (
            <div className="mx-auto max-w-[var(--measure-read)]">
              <p
                className="ijg-eyebrow mb-2.5"
                style={{ color: "var(--text-3)" }}
              >
                이 장의 낱말
              </p>
              <div className="flex flex-wrap gap-2.5">
                {done.words.map((w) => (
                  <WordChip key={w} term={w} onClick={() => void lookUp(w)} />
                ))}
              </div>
            </div>
          )}

          {isLastChapter && !canGoNext && (
            <p
              role="status"
              aria-live="polite"
              className="mt-8 text-center text-[length:var(--text-md)] font-bold"
              style={{ color: "var(--success-text)" }}
            >
              이야기를 모두 읽었어요!
            </p>
          )}

          <div className="mt-9 flex flex-wrap justify-center gap-3">
            {mode === "free" && !reviseOpen && !revising && (
              <Button
                variant="outline"
                icon="wand-sparkles"
                onClick={() => setReviseOpen(true)}
              >
                이야기 고치기
              </Button>
            )}

            {canGoNext ? (
              <Button iconRight="arrow-right" onClick={onNext}>
                다음 장으로
              </Button>
            ) : isLastChapter ? null : (
              <Button variant="outline" icon="refresh-cw" onClick={onRetry}>
                다시 확인할래요
              </Button>
            )}

            <Link
              href={`/books/${bookId}/learn`}
              className={buttonClass("accent", "md")}
            >
              <Icon name="graduation-cap" size={18} />
              학습 활동 하러 가기
            </Link>
          </div>

          {!canGoNext && !isLastChapter && (
            <p className="mt-3 text-center text-[length:var(--text-sm)] font-bold text-ink-2">
              다음 장을 준비하고 있어요. 잠시 후 다시 확인해 주세요.
            </p>
          )}
        </div>
      )}

      {/* 자유모드 수정요청: 다 쓰인 자유 챕터에서 본문을 고쳐 달라고 요청. */}
      {revealed && done && mode === "free" && (reviseOpen || revising) && (
        <Card padding="md" className="mx-auto mt-4 max-w-[var(--measure-read)]">
          {revising ? (
            <p
              role="status"
              aria-live="polite"
              className="ijg-caret text-center font-bold"
              style={{ color: "var(--accent-text)" }}
            >
              이야기를 고치고 있어요… 잠시만 기다려 주세요.
            </p>
          ) : (
            <>
              <label className="flex flex-col gap-2">
                <span className="font-bold text-ink">어떻게 고칠까요?</span>
                <Textarea
                  value={reviseText}
                  onChange={(e) => setReviseText(e.target.value)}
                  rows={3}
                  placeholder="예) 주인공을 더 씩씩하게 바꿔 줘"
                />
              </label>
              {reviseError && <ErrorText className="mt-2">{reviseError}</ErrorText>}
              <div className="mt-3 flex gap-2">
                <Button
                  onClick={() => void submitRevise()}
                  disabled={!reviseText.trim()}
                  className="flex-1"
                >
                  고쳐 주세요
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setReviseOpen(false);
                    setReviseError(null);
                  }}
                >
                  취소
                </Button>
              </div>
            </>
          )}
        </Card>
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

/**
 * 삽화 — 로드 실패하거나 식별자 글자가 박힌 placeholder(placehold.co)면
 * 코드 문자열 대신 중립 표시(아이콘 + alt 캡션)로 폴백한다. (07)
 */
function Illustration({ url, alt }: { url: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  const isPlaceholder = /placehold\.co/i.test(url);

  if (failed || isPlaceholder) {
    return (
      <div
        role="img"
        aria-label={alt}
        className="mb-4 flex h-[16rem] w-full flex-col items-center justify-center gap-2 rounded-[var(--radius-card)]"
        style={{
          background: "var(--surface-2)",
          border: "var(--border) solid var(--line)",
        }}
      >
        <Icon
          name="image"
          size={40}
          strokeWidth={1.5}
          style={{ color: "var(--text-faint)" }}
        />
        <span
          className="px-4 text-center text-[length:var(--text-sm)]"
          style={{ color: "var(--text-3)" }}
        >
          {alt}
        </span>
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt={alt}
      onError={() => setFailed(true)}
      className="mb-4 max-h-[28rem] w-full rounded-[var(--radius-card)] object-cover shadow-[var(--elev-md)]"
    />
  );
}

function WordChip({ term, onClick }: { term: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        height: 38,
        padding: "0 14px",
        background: "var(--surface-2)",
        border: "var(--border) solid var(--line)",
        borderRadius: 999,
        fontFamily: "var(--font-body)",
        fontWeight: 700,
        fontSize: "var(--text-sm)",
        color: "var(--text-1)",
        cursor: "pointer",
      }}
    >
      <Icon name="volume-2" size={15} style={{ color: "var(--primary)" }} />
      {term}
    </button>
  );
}
