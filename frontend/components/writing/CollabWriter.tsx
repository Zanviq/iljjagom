"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
import { Loading } from "@/components/ui/Loading";
import { Textarea } from "@/components/ui/Textarea";
import { TypingIndicator } from "@/components/ui/TypingIndicator";
import { ApiError, getCollab, postCollab } from "@/lib/api";
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
 * CollabWriter — 자유집필(기·승) 2단 협업(04 기능개선 학생/15).
 * 좌: 학생↔AI가 한 문단씩 쌓는 본문. 우: 진행 질문·지도 대화 + 입력.
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

  function applyReply(reply: CollabReply) {
    if (reply.kind === "paragraph" && reply.paragraph) {
      setParagraphs((p) => [...p, { ...reply.paragraph!, source: "collab" }]);
      setCoaching(null);
      if (reply.question) {
        setTurns((t) => [
          ...t,
          {
            role: "writer",
            kind: "question",
            content: reply.question!,
            createdAt: "",
          },
        ]);
      }
    } else if (reply.kind === "coaching" && reply.coaching) {
      setCoaching({ ...reply.coaching, intent: lastIntentRef.current });
      setTurns((t) => [
        ...t,
        {
          role: "writer",
          kind: "coaching",
          content: reply.coaching!.text,
          createdAt: "",
        },
      ]);
    } else {
      setTurns((t) => [
        ...t,
        {
          role: "writer",
          kind: "message",
          content: "음, 무슨 이야기인지 한 번 더 말해 줄래?",
          createdAt: "",
        },
      ]);
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

  if (loading) {
    return <Loading card>이야기를 준비하는 중이에요…</Loading>;
  }

  return (
    <div className="grid items-start gap-[22px] [grid-template-columns:1fr] md:[grid-template-columns:1.55fr_1fr]">
      {/* 좌: 본문 누적 */}
      <Card padding="lg" style={{ minHeight: 460 }}>
        <p className="ijg-eyebrow mb-3" style={{ color: "var(--primary-text)" }}>
          우리가 쓰는 이야기
        </p>
        {paragraphs.length === 0 ? (
          <EmptyState icon="feather" title="아직 빈 이야기예요">
            오른쪽에서 곰 작가와 한 문단씩 함께 써 봐요.
          </EmptyState>
        ) : (
          <div className="flex flex-col gap-4">
            {paragraphs.map((p) => (
              <p
                key={p.seq}
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
            ))}
          </div>
        )}
      </Card>

      {/* 우: AI 대화 + 입력 */}
      <Card
        padding="none"
        style={{
          display: "flex",
          flexDirection: "column",
          height: 460,
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
              onClick={() => router.push(`/books/${bookId}/mid-activity`)}
            >
              이야기 이어보기
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
              placeholder="다음엔 어떤 일이 생길까?"
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
