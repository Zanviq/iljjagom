"use client";

import { useState } from "react";

import { buttonClass } from "@/components/ui/Button";
import { ErrorText } from "@/components/ui/ErrorText";
import { ApiError, postLetter } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { LetterReply } from "@/lib/types";

export function LetterForm({ bookId }: { bookId: string }) {
  const [to, setTo] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [reply, setReply] = useState<LetterReply | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    const toName = to.trim();
    const bodyText = body.trim();
    if (!toName || !bodyText || sending) return;
    setSending(true);
    setError(null);
    setReply(null);
    try {
      const token = await getClientAccessToken();
      const res = await postLetter(token, bookId, toName, bodyText);
      setReply(res);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "편지를 보내지 못했어요.",
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="rounded-card bg-surface p-5 ring-1 ring-border">
      <label className="flex flex-col gap-2">
        <span className="font-bold">누구에게 편지를 쓸까요?</span>
        <input
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="이야기 속 인물 이름"
          className="h-12 rounded-xl border-2 border-border bg-background px-4 text-lg"
        />
      </label>
      <label className="mt-3 flex flex-col gap-2">
        <span className="font-bold">편지 내용</span>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
          placeholder="하고 싶은 말을 적어 봐요."
          className="rounded-xl border-2 border-border bg-background p-3 text-lg"
        />
      </label>

      {error && <ErrorText className="mt-2">{error}</ErrorText>}

      <button
        onClick={() => void send()}
        disabled={!to.trim() || !body.trim() || sending}
        className={buttonClass("primary", "md", "mt-4 w-full")}
      >
        {sending ? "보내는 중…" : "편지 보내기"}
      </button>

      {reply && (
        <div className="mt-4 rounded-xl bg-accent/20 p-4">
          {reply.status === "held" ? (
            <p className="font-bold text-secondary-strong">
              💌 편지를 잘 받았어요. 선생님이 확인한 뒤 답장을 줄 거예요.
            </p>
          ) : (
            <>
              <p className="text-xs font-bold text-muted">
                {to.trim()}의 답장
              </p>
              <p className="mt-1 whitespace-pre-wrap text-lg">{reply.reply}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
