"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AskUserPanel } from "@/components/ai/AskUserPanel";
import { CharacterCard } from "@/components/planning/CharacterCard";
import { buttonClass } from "@/components/ui/Button";
import { ErrorText } from "@/components/ui/ErrorText";
import { ApiError, getBook, postDesign, postPlanMessage } from "@/lib/api";
import { answerAiSession } from "@/lib/ai";
import type { AskUserAnswer, AskUserPrompt } from "@/lib/ai";
import { getClientAccessToken } from "@/lib/auth/client";
import type { PlanReply } from "@/lib/types";

/** ask_user 가 plan 응답에 실려오는 경우(백엔드 계약 확정 시 PlanReply로 승격). */
function extractAsk(reply: PlanReply): AskUserPrompt | null {
  const ask = (reply as PlanReply & { ask?: AskUserPrompt }).ask;
  return ask && ask.sessionId && ask.question ? ask : null;
}

interface Message {
  who: "child" | "ai";
  text: string;
}

const INTRO: Message = {
  who: "ai",
  text: "안녕! 우리 함께 멋진 이야기를 만들어 보자. 어떤 주인공이 나오면 좋겠어?",
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function PlanChat({ bookId }: { bookId: string }) {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([INTRO]);
  const [draft, setDraft] = useState<PlanReply["characterDraft"]>({
    name: null,
    traits: [],
  });
  const [readyToWrite, setReadyToWrite] = useState(false);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [designing, setDesigning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ask, setAsk] = useState<AskUserPrompt | null>(null);
  const [answering, setAnswering] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);

  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    setError(null);
    setInput("");
    setMessages((m) => [...m, { who: "child", text }]);
    setSending(true);
    try {
      const token = await getClientAccessToken();
      const reply = await postPlanMessage(token, bookId, text);
      setMessages((m) => [...m, { who: "ai", text: reply.reply }]);
      setDraft(reply.characterDraft);
      setReadyToWrite(reply.readyToWrite);
      setAsk(extractAsk(reply));
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "메시지를 보내지 못했어요.",
      );
    } finally {
      setSending(false);
    }
  }

  async function submitAnswer(answer: AskUserAnswer) {
    if (!ask || answering) return;
    setAskError(null);
    setAnswering(true);
    const shown =
      answer.text ??
      (answer.choice !== undefined ? ask.choices[answer.choice] : "");
    try {
      const token = await getClientAccessToken();
      await answerAiSession(token, ask.sessionId, answer);
      if (shown) setMessages((m) => [...m, { who: "child", text: shown }]);
      setAsk(null);
      // 흐름 재개 응답 형태는 백엔드 확정 대기(handoff). 확정되면 후속 reply를 이어붙인다.
    } catch (e) {
      setAskError(
        e instanceof ApiError ? e.message : "대답을 전하지 못했어요.",
      );
    } finally {
      setAnswering(false);
    }
  }

  async function startWriting() {
    if (designing) return;
    setError(null);
    setDesigning(true);
    try {
      const token = await getClientAccessToken();
      const ds = await postDesign(token, bookId);
      const readPath = `/books/${bookId}/read`;
      if (ds.status === "done") {
        router.push(readPath);
        return;
      }
      // 설계가 진행 중이면 책 상태가 바뀔 때까지 잠깐 기다린다.
      for (let i = 0; i < 15; i++) {
        await sleep(1000);
        const book = await getBook(token, bookId);
        if (book.status !== "planning") break;
      }
      router.push(readPath);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "이야기를 시작하지 못했어요.",
      );
      setDesigning(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
      <div className="flex min-h-[60vh] flex-col rounded-card bg-surface ring-1 ring-border">
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.map((m, i) => (
            <Bubble key={i} who={m.who} text={m.text} />
          ))}
          {sending && <Bubble who="ai" text="음… 생각 중이야 ✏️" muted />}
          <div ref={endRef} />
        </div>

        {error && (
          <ErrorText className="px-5 pb-2">{error}</ErrorText>
        )}

        {ask && (
          <div className="border-t border-border p-4">
            <AskUserPanel
              prompt={ask}
              pending={answering}
              error={askError}
              onAnswer={(a) => void submitAnswer(a)}
            />
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
          className={`flex items-end gap-2 border-t border-border p-4 ${
            ask ? "hidden" : ""
          }`}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            rows={1}
            placeholder="이야기를 들려줘…"
            disabled={designing}
            className="max-h-32 flex-1 resize-none rounded-xl border-2 border-border bg-background px-4 py-3 text-lg"
          />
          <button
            type="submit"
            disabled={sending || designing || !input.trim()}
            className={buttonClass("primary", "md")}
          >
            보내기
          </button>
        </form>
      </div>

      <div className="space-y-4">
        <CharacterCard draft={draft} />

        <div className="rounded-card bg-surface p-5 ring-1 ring-border">
          <p className="text-sm text-muted">
            {readyToWrite
              ? "이제 이야기를 시작할 준비가 됐어요!"
              : "주인공과 이야기를 더 들려주면 시작 버튼이 켜져요."}
          </p>
          <button
            onClick={() => void startWriting()}
            disabled={!readyToWrite || designing}
            className={buttonClass("secondary", "lg", "mt-3 w-full")}
          >
            {designing ? "이야기 준비 중…" : "✨ 이야기 시작하기"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Bubble({
  who,
  text,
  muted,
}: {
  who: "child" | "ai";
  text: string;
  muted?: boolean;
}) {
  const isChild = who === "child";
  return (
    <div className={isChild ? "flex justify-end" : "flex justify-start"}>
      <div
        className={[
          "max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-lg",
          isChild
            ? "bg-primary text-primary-foreground"
            : "bg-background ring-1 ring-border",
          muted ? "opacity-70" : "",
        ].join(" ")}
      >
        {text}
      </div>
    </div>
  );
}
