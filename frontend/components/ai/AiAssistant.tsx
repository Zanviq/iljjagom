"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { Icon } from "@/components/ui/Icon";
import { Textarea } from "@/components/ui/Textarea";
import { TypingIndicator } from "@/components/ui/TypingIndicator";
import { ApiError } from "@/lib/api";
import { postOverseerMessage, type OverseerAction } from "@/lib/ai";
import { getClientAccessToken } from "@/lib/auth/client";

/** 노출 라우트: 학생 메인(/home)만. 도서 제작/독서(plan·read)에는 버튼 없음(몰입 보호). */
function isExposed(pathname: string): boolean {
  return pathname === "/home";
}

interface Msg {
  from: "ai" | "me";
  text: string;
  actions?: OverseerAction[];
}

const INTRO: Msg = {
  from: "ai",
  text: "무엇이든 물어봐! 새 책을 만들고 싶거나, 읽던 이야기를 이어가고 싶으면 말해 줘.",
};

/**
 * 총괄(Overseer) AI — 곰 작가 사이드바(new-design_version2 StudentShell AiFab/AiDrawer).
 * 말하면 POST /ai/overseer/messages → reply + 이동 액션(버튼) 렌더. auto:true면 즉시 이동.
 */
export function AiAssistant() {
  const pathname = usePathname() || "";
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([INTRO]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, open, sending]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  if (!isExposed(pathname)) return null;

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setMsgs((m) => [...m, { from: "me", text }]);
    setSending(true);
    try {
      const token = await getClientAccessToken();
      const res = await postOverseerMessage(token, text, sessionId, pathname);
      setSessionId(res.sessionId);
      setMsgs((m) => [
        ...m,
        { from: "ai", text: res.reply, actions: res.actions },
      ]);
      const auto = res.actions.find((a) => a.auto);
      if (auto) router.push(auto.to);
    } catch (e) {
      setMsgs((m) => [
        ...m,
        {
          from: "ai",
          text:
            e instanceof ApiError
              ? "지금은 대답하기 어려워. 잠시 후 다시 물어봐 줄래?"
              : "연결이 잘 안 됐어. 잠시 후 다시 시도해 줘.",
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      {/* 백드롭 */}
      <div
        onClick={() => setOpen(false)}
        aria-hidden
        className="fixed inset-0 z-40 transition-opacity"
        style={{
          background: "rgba(42,32,24,.34)",
          opacity: open ? 1 : 0,
          pointerEvents: open ? "auto" : "none",
        }}
      />

      {/* 드로어 */}
      <aside
        aria-label="곰 작가"
        className="fixed bottom-0 right-0 top-0 z-50 flex w-[min(400px,92vw)] flex-col border-l border-line bg-surface shadow-[var(--elev-lg)]"
        style={{
          transform: open ? "translateX(0)" : "translateX(102%)",
          transition: "transform var(--dur-slow) var(--ease-env)",
        }}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-[18px]">
          <div className="flex items-center gap-2.5">
            <span
              className="flex h-[34px] w-[34px] items-center justify-center rounded-[10px] bg-primary text-on-primary"
              aria-hidden
            >
              <Icon name="sparkles" size={18} />
            </span>
            <div>
              <p className="font-extrabold text-ink">곰 작가</p>
              <p className="text-[length:var(--text-xs)] text-ink-3">
                무엇이든 물어봐요
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" icon="x" aria-label="닫기" onClick={() => setOpen(false)} />
        </div>

        <div className="flex flex-1 flex-col gap-3.5 overflow-y-auto p-5">
          {msgs.map((m, i) => (
            <div key={i} className="flex flex-col gap-2">
              <ChatBubble from={m.from} name={m.from === "ai" ? "곰 작가" : undefined}>
                <span className="whitespace-pre-wrap">{m.text}</span>
              </ChatBubble>
              {m.actions && m.actions.length > 0 && (
                <div className="flex flex-wrap gap-2 pl-11">
                  {m.actions.map((a, ai) => (
                    <Button
                      key={ai}
                      size="sm"
                      iconRight="arrow-right"
                      onClick={() => router.push(a.to)}
                    >
                      {a.label}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {sending && (
            <ChatBubble from="ai" name="곰 작가">
              <TypingIndicator />
            </ChatBubble>
          )}
          <div ref={endRef} />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
          className="flex items-end gap-2 border-t border-line p-4"
        >
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onSubmit={() => void send()}
            autoGrow
            placeholder="질문을 적어요"
            aria-label="곰 작가에게 질문"
            disabled={sending}
            className="flex-1"
          />
          <Button type="submit" icon="send" aria-label="보내기" disabled={sending || !input.trim()} className="flex-none" />
        </form>
      </aside>

      {/* FAB */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-30 inline-flex h-[54px] items-center gap-2 rounded-full bg-primary pl-[18px] pr-[22px] font-extrabold text-on-primary"
          style={{ boxShadow: "var(--elev-pop)" }}
        >
          <Icon name="sparkles" size={20} />
          곰 작가에게 물어보기
        </button>
      )}
    </>
  );
}
