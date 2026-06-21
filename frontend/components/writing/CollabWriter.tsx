"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
import { Icon } from "@/components/ui/Icon";
import { Loading } from "@/components/ui/Loading";
import { Textarea } from "@/components/ui/Textarea";
import { TypingIndicator } from "@/components/ui/TypingIndicator";
import {
  ApiError,
  getBook,
  getCollab,
  patchParagraph,
  postCollab,
  reorderParagraphs,
} from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type {
  CollabReply,
  CollabStateParagraph,
  CollabTurn,
} from "@/lib/types";

const INTRO_QUESTION =
  "이 이야기, 어떻게 시작할까? 떠오르는 첫 장면을 말해 줘!";

/** 직전 지도(coaching) — 수용/고수 시 유발 메시지를 다시 보낸다. */
interface Coaching {
  text: string;
  reasons: string[];
  intent: string;
}

/**
 * CollabWriter — 자유집필(기·승) 2단 협업(학생/15 + 05-기능수정 §02).
 * 좌: 문단을 '섹션 카드'로(좌상단 밖 번호·드래그 순서변경·수정버튼 직접편집).
 * 우: 진행 질문·지도 대화 + 입력. 직접편집/대화수정/순서변경은 모두 AI에 동기화된다.
 * 협업 엔드포인트 미구현(404)이면 기존 독서 화면으로 폴백(현 동작 보존).
 */
export function CollabWriter({
  bookId,
  chapterIdx,
}: {
  bookId: string;
  chapterIdx: number;
}) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [paragraphs, setParagraphs] = useState<CollabStateParagraph[]>([]);
  const [turns, setTurns] = useState<CollabTurn[]>([]);
  const [coaching, setCoaching] = useState<Coaching | null>(null);
  const [chapterComplete, setChapterComplete] = useState(false);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 직접편집·순서변경 상태.
  const [editingSeq, setEditingSeq] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [flashSeq, setFlashSeq] = useState<number | null>(null);
  const [nextHref, setNextHref] = useState<string | null>(null);
  const dragSeq = useRef<number | null>(null);

  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, sending]);

  // 초기 복원: 좌(문단)·우(대화). 미구현이면 독서로 폴백.
  useEffect(() => {
    let active = true;
    (async () => {
      const t = await getClientAccessToken();
      if (!active) return;
      setToken(t);
      try {
        const state = await getCollab(t, bookId, chapterIdx);
        if (!active) return;
        setParagraphs(state.paragraphs);
        setTurns(state.turns);
        setChapterComplete(state.chapterComplete);
      } catch (e) {
        if (!active) return;
        if (e instanceof ApiError && (e.status === 404 || e.status === 0)) {
          router.replace(`/books/${bookId}/read`);
          return;
        }
        setError(
          e instanceof ApiError ? e.message : "이야기를 불러오지 못했어요.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [bookId, chapterIdx, router]);

  // 챕터 완료 시 다음 목적지 결정: 다음 free 챕터가 남았으면 그 협업으로, 아니면 중간활동(§03).
  useEffect(() => {
    if (!chapterComplete || !token) return;
    let active = true;
    (async () => {
      const COLLAB_TARGET = 4;
      try {
        const book = await getBook(token, bookId);
        const nextFree = book.chapters
          .filter((c) => c.mode === "free")
          .sort((a, b) => a.idx - b.idx)
          .find(
            (c) => c.idx > chapterIdx && (c.paragraphCount ?? 0) < COLLAB_TARGET,
          );
        if (active)
          setNextHref(
            nextFree
              ? `/books/${bookId}/write?idx=${nextFree.idx}`
              : `/books/${bookId}/mid-activity`,
          );
      } catch {
        if (active) setNextHref(`/books/${bookId}/mid-activity`);
      }
    })();
    return () => {
      active = false;
    };
  }, [chapterComplete, token, bookId, chapterIdx]);

  function flash(seq: number) {
    setFlashSeq(seq);
    window.setTimeout(() => setFlashSeq((s) => (s === seq ? null : s)), 1300);
  }

  function pushWriterTurn(kind: CollabTurn["kind"], content: string) {
    setTurns((t) => [...t, { role: "writer", kind, content, createdAt: "" }]);
  }

  function applyReply(reply: CollabReply) {
    if (reply.kind === "paragraph" && reply.paragraph) {
      const para = reply.paragraph;
      if (reply.replacedSeq != null) {
        // 대화수정: 새 문단 추가가 아니라 대상 문단 교체.
        const target = reply.replacedSeq;
        setParagraphs((ps) =>
          ps.map((p) =>
            p.seq === target ? { ...p, body: para.body, source: "revise" } : p,
          ),
        );
        flash(target);
      } else {
        setParagraphs((p) => [...p, { ...para, source: "collab" }]);
      }
      setCoaching(null);
      if (reply.question) pushWriterTurn("question", reply.question);
      if (reply.suggestion) pushWriterTurn("coaching", reply.suggestion);
    } else if (reply.kind === "coaching" && reply.coaching) {
      setCoaching({ ...reply.coaching, intent: lastIntentRef.current });
      pushWriterTurn("coaching", reply.coaching.text);
    } else {
      pushWriterTurn("message", "음, 무슨 이야기인지 한 번 더 말해 줄래?");
    }
    setChapterComplete(reply.chapterComplete);
  }

  // 지도 수용/고수 버튼이 다시 보낼 학생 의도.
  const lastIntentRef = useRef("");

  async function send(message: string, accept?: boolean) {
    const text = message.trim();
    if (!text || sending) return;
    setError(null);
    lastIntentRef.current = text;
    // accept(버튼) 응답이면 학생 말풍선을 새로 만들지 않는다(이미 표시됨).
    if (accept === undefined) {
      setTurns((t) => [
        ...t,
        { role: "student", kind: "message", content: text, createdAt: "" },
      ]);
      setInput("");
    }
    setCoaching(null);
    setSending(true);
    try {
      const reply = await postCollab(token, bookId, chapterIdx, text, accept);
      applyReply(reply);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "문단을 만들지 못했어요.");
    } finally {
      setSending(false);
    }
  }

  function startEdit(p: CollabStateParagraph) {
    setEditingSeq(p.seq);
    setEditText(p.body);
  }

  async function saveEdit(seq: number) {
    const body = editText.trim();
    if (!body || savingEdit) return;
    setSavingEdit(true);
    setError(null);
    try {
      const res = await patchParagraph(token, bookId, chapterIdx, seq, body);
      setParagraphs((ps) =>
        ps.map((p) =>
          p.seq === seq
            ? { ...p, body: res.paragraph.body, source: "revise" }
            : p,
        ),
      );
      setEditingSeq(null);
      flash(seq);
      if (res.suggestion) pushWriterTurn("coaching", res.suggestion);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "문단을 고치지 못했어요.");
    } finally {
      setSavingEdit(false);
    }
  }

  /** fromSeq 문단을 toIndex 위치로 이동(드래그·키보드 공용). */
  async function moveTo(fromSeq: number, toIndex: number) {
    const cur = [...paragraphs];
    const fromIndex = cur.findIndex((p) => p.seq === fromSeq);
    if (
      fromIndex < 0 ||
      toIndex < 0 ||
      toIndex >= cur.length ||
      fromIndex === toIndex
    )
      return;
    const [moved] = cur.splice(fromIndex, 1);
    cur.splice(toIndex, 0, moved);
    const order = cur.map((p) => p.seq); // 현재 seq 들의 새 순서
    setParagraphs(cur.map((p, i) => ({ ...p, seq: i + 1 }))); // 낙관적
    try {
      const res = await reorderParagraphs(token, bookId, chapterIdx, order);
      setParagraphs(res.paragraphs);
    } catch {
      try {
        const state = await getCollab(token, bookId, chapterIdx);
        setParagraphs(state.paragraphs);
      } catch {
        /* noop */
      }
      setError("순서를 바꾸지 못했어요.");
    }
  }

  if (loading) {
    return <Loading card>이야기를 준비하는 중이에요…</Loading>;
  }

  // 화면 높이에 따라 두 박스가 유연하게(세로로) 늘고 줄도록 — 고정 정사각 방지(06 §화면조절).
  const PANEL_H = "clamp(420px, 70vh, 820px)";
  return (
    <div className="grid items-start gap-[22px] [grid-template-columns:1fr] md:[grid-template-columns:1.55fr_1fr]">
      {/* 좌: 본문 누적(섹션 카드) */}
      <Card padding="lg" style={{ minHeight: PANEL_H, overflow: "visible" }}>
        <p className="ijg-eyebrow mb-4" style={{ color: "var(--primary-text)" }}>
          우리가 쓰는 이야기
        </p>
        {paragraphs.length === 0 ? (
          <EmptyState icon="feather" title="아직 빈 이야기예요">
            오른쪽에서 곰 작가와 한 문단씩 함께 써 봐요.
          </EmptyState>
        ) : (
          <div className="flex flex-col gap-5 pl-3">
            {paragraphs.map((p, i) => {
              const editing = editingSeq === p.seq;
              return (
                <section
                  key={p.seq}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => {
                    if (dragSeq.current != null) void moveTo(dragSeq.current, i);
                    dragSeq.current = null;
                  }}
                  className="relative rounded-[var(--radius-md)] border bg-surface p-4 transition-colors"
                  style={{
                    borderColor:
                      flashSeq === p.seq ? "var(--primary)" : "var(--line)",
                    boxShadow:
                      flashSeq === p.seq ? "var(--elev-sm)" : undefined,
                  }}
                >
                  {/* 번호 배지 — 카드 좌상단 바깥 */}
                  <span
                    aria-hidden
                    className="absolute flex h-7 w-7 items-center justify-center rounded-full bg-primary text-[length:var(--text-sm)] font-extrabold text-on-primary"
                    style={{ top: -12, left: -14, boxShadow: "var(--elev-sm)" }}
                  >
                    {i + 1}
                  </span>

                  {/* 도구: 드래그 핸들 · 순서 · 수정 */}
                  {!editing && (
                    <div className="mb-2 flex items-center justify-end gap-1">
                      <span
                        draggable
                        onDragStart={() => {
                          dragSeq.current = p.seq;
                        }}
                        onDragEnd={() => {
                          dragSeq.current = null;
                        }}
                        role="button"
                        aria-label="끌어서 순서 바꾸기"
                        className="cursor-grab p-1 text-ink-3 active:cursor-grabbing"
                      >
                        <Icon name="grip-vertical" size={16} />
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon="arrow-left"
                        aria-label="위로"
                        className="rotate-90"
                        disabled={i === 0}
                        onClick={() => void moveTo(p.seq, i - 1)}
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        icon="arrow-right"
                        aria-label="아래로"
                        className="rotate-90"
                        disabled={i === paragraphs.length - 1}
                        onClick={() => void moveTo(p.seq, i + 1)}
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        icon="pencil"
                        aria-label="문단 수정"
                        onClick={() => startEdit(p)}
                      >
                        수정
                      </Button>
                    </div>
                  )}

                  {editing ? (
                    <div className="flex flex-col gap-2">
                      <Textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        autoGrow
                        aria-label={`${i + 1}번 문단 수정`}
                        disabled={savingEdit}
                      />
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditingSeq(null)}
                          disabled={savingEdit}
                        >
                          취소
                        </Button>
                        <Button
                          size="sm"
                          icon="save"
                          onClick={() => void saveEdit(p.seq)}
                          disabled={savingEdit || !editText.trim()}
                        >
                          저장
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p
                      className="whitespace-pre-wrap"
                      style={{
                        fontFamily: "var(--font-serif)",
                        fontSize: "var(--text-lg)",
                        lineHeight: "var(--leading-normal)",
                        color: "var(--text-1)",
                      }}
                    >
                      {p.body}
                    </p>
                  )}
                </section>
              );
            })}
          </div>
        )}
      </Card>

      {/* 우: AI 대화 + 입력 — 화면 높이에 맞춰 늘고, 긴 이야기에선 따라오도록 sticky. */}
      <Card
        padding="none"
        className="md:sticky md:top-6"
        style={{
          display: "flex",
          flexDirection: "column",
          height: PANEL_H,
          overflow: "hidden",
        }}
      >
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-[22px]">
          {turns.length === 0 && (
            <ChatBubble from="ai" name="곰 작가">
              <span className="whitespace-pre-wrap">{INTRO_QUESTION}</span>
            </ChatBubble>
          )}
          {turns.map((m, i) => (
            <ChatBubble
              key={i}
              from={m.role === "student" ? "me" : "ai"}
              name={m.role === "writer" ? "곰 작가" : undefined}
            >
              <span className="whitespace-pre-wrap">{m.content}</span>
            </ChatBubble>
          ))}

          {coaching && !sending && (
            <div className="flex flex-col gap-2 pl-11">
              {coaching.reasons.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {coaching.reasons.map((r, i) => (
                    <Chip key={i} icon="sparkles">
                      {r}
                    </Chip>
                  ))}
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  icon="check"
                  onClick={() => void send(coaching.intent, true)}
                >
                  제안대로 할래요
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void send(coaching.intent, false)}
                >
                  이대로 갈래요
                </Button>
              </div>
            </div>
          )}

          {sending && (
            <ChatBubble from="ai" name="곰 작가">
              <TypingIndicator />
            </ChatBubble>
          )}
          <div ref={endRef} />
        </div>

        {error && <ErrorText className="px-[22px] pb-2">{error}</ErrorText>}

        {chapterComplete ? (
          <div className="flex flex-col items-center gap-3 border-t border-line bg-surface-inset p-4">
            <p
              role="status"
              aria-live="polite"
              className="text-center text-[length:var(--text-md)] font-bold"
              style={{ color: "var(--success-text)" }}
            >
              이 장을 멋지게 완성했어요!
            </p>
            <Button
              iconRight="arrow-right"
              onClick={() =>
                router.push(nextHref ?? `/books/${bookId}/mid-activity`)
              }
            >
              {nextHref?.includes("/write")
                ? "다음 이야기 함께 쓰기"
                : "이야기 이어보기"}
            </Button>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void send(input);
            }}
            className="flex items-end gap-2.5 border-t border-line bg-surface-inset p-4"
          >
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onSubmit={() => void send(input)}
              autoGrow
              placeholder="다음엔 어떤 일이 생길까? (예: 두번째 문단을 더 재미있게 고쳐줘)"
              disabled={sending}
              aria-label="이야기 입력"
              className="flex-1"
            />
            <Button
              type="submit"
              icon="send"
              disabled={sending || !input.trim()}
              className="flex-none"
            >
              보내기
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
