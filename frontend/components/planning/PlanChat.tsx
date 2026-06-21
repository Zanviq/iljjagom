"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AskUserPanel } from "@/components/ai/AskUserPanel";
import { CharacterCard } from "@/components/planning/CharacterCard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { ErrorText } from "@/components/ui/ErrorText";
import { Textarea } from "@/components/ui/Textarea";
import { TypingIndicator } from "@/components/ui/TypingIndicator";
import { ApiError, getBook, postDesign, postPlanMessage } from "@/lib/api";
import { answerAiSession } from "@/lib/ai";
import type { AskUserAnswer, AskUserPrompt } from "@/lib/ai";
import { getClientAccessToken } from "@/lib/auth/client";
import type { PlanReply } from "@/lib/types";

/** ask_user 가 plan 응답에 실려오면(PlanReply.ask) 질문 패널을 띄운다. */
function extractAsk(reply: PlanReply): AskUserPrompt | null {
  const ask = reply.ask;
  return ask && ask.sessionId && ask.question ? ask : null;
}

interface Message {
  who: "child" | "ai";
  text: string;
}

const INTRO: Message = {
  who: "ai",
  text: "안녕! 오늘은 어떤 주인공이 나오는 이야기를 만들어 볼까?",
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
      setError(e instanceof ApiError ? e.message : "메시지를 보내지 못했어요.");
    } finally {
      setSending(false);
    }
  }

  async function submitAnswer(answer: AskUserAnswer) {
    if (!ask || answering) return;
    setAskError(null);
    setAnswering(true);
    const shown = answer.text ?? answer.choice ?? "";
    try {
      const token = await getClientAccessToken();
      await answerAiSession(token, ask.sessionId, answer);
      if (shown) setMessages((m) => [...m, { who: "child", text: shown }]);
      setAsk(null);
      // 흐름 재개 응답 형태는 백엔드 확정 대기(handoff). 확정되면 후속 reply를 이어붙인다.
    } catch (e) {
      setAskError(e instanceof ApiError ? e.message : "대답을 전하지 못했어요.");
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
      // 설계가 진행 중이면 책 상태가 바뀔 때까지 잠깐 기다린다.
      if (ds.status !== "done") {
        for (let i = 0; i < 15; i++) {
          await sleep(1000);
          const book = await getBook(token, bookId);
          if (book.status !== "planning") break;
        }
      }
      // 자유집필(free) 첫 챕터면 협업 화면(/write), 아니면 독서(/read)로.
      let dest = `/books/${bookId}/read`;
      try {
        const book = await getBook(token, bookId);
        const first = [...book.chapters].sort((a, b) => a.idx - b.idx)[0];
        if (first?.mode === "free") dest = `/books/${bookId}/write`;
      } catch {
        // 책 조회 실패 시 기본 독서 경로 유지.
      }
      router.push(dest);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "이야기를 시작하지 못했어요.");
      setDesigning(false);
    }
  }

  // 대화창이 화면 높이에 맞춰 유연하게(세로로) 늘고 줄도록 — 고정 정사각 방지(화면조절).
  const PANEL_H = "clamp(420px, 70vh, 820px)";
  return (
    <div className="grid items-start gap-[22px] [grid-template-columns:1fr] md:[grid-template-columns:1.55fr_1fr]">
      <Card padding="none" style={{ display: "flex", flexDirection: "column", height: PANEL_H, overflow: "hidden" }}>
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-[22px]">
          {messages.map((m, i) => (
            <ChatBubble
              key={i}
              from={m.who === "child" ? "me" : "ai"}
              name={m.who === "ai" ? "곰 작가" : undefined}
            >
              <span className="whitespace-pre-wrap">{m.text}</span>
            </ChatBubble>
          ))}
          {sending && (
            <ChatBubble from="ai" name="곰 작가">
              <TypingIndicator />
            </ChatBubble>
          )}
          <div ref={endRef} />
        </div>

        {error && <ErrorText className="px-[22px] pb-2">{error}</ErrorText>}

        {ask && (
          <div className="border-t border-line p-4">
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
          className={`flex items-end gap-2.5 border-t border-line bg-surface-inset p-4 ${
            ask ? "hidden" : ""
          }`}
        >
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onSubmit={() => void send()}
            autoGrow
            placeholder="여기에 이야기를 적어요"
            disabled={designing}
            aria-label="이야기 입력"
            className="flex-1"
          />
          <Button
            type="submit"
            icon="send"
            disabled={sending || designing || !input.trim()}
            className="flex-none"
          >
            보내기
          </Button>
        </form>
      </Card>

      <div className="flex flex-col gap-4">
        <CharacterCard draft={draft} />
        <Button
          size="lg"
          icon="wand-sparkles"
          fullWidth
          onClick={() => void startWriting()}
          disabled={!readyToWrite || designing}
        >
          {designing ? "이야기 준비 중…" : "이야기 시작하기"}
        </Button>
        <p className="text-center text-[length:var(--text-sm)] text-ink-3">
          {readyToWrite
            ? "이제 이야기를 시작할 준비가 됐어요!"
            : "주인공과 이야기를 더 들려주면 시작 버튼이 켜져요."}
        </p>
      </div>
    </div>
  );
}
