"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { ErrorText } from "@/components/ui/ErrorText";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { ApiError, postLetter } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { LetterCharacter, LetterReply } from "@/lib/types";

export function LetterForm({
  bookId,
  characters,
}: {
  bookId: string;
  characters?: LetterCharacter[];
}) {
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
      setError(e instanceof ApiError ? e.message : "편지를 보내지 못했어요.");
    } finally {
      setSending(false);
    }
  }

  // 답장(answered)을 받으면 보낸 편지 + 답장을 대화 버블로 보여 준다.
  if (reply && reply.status !== "held") {
    return (
      <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <ChatBubble from="me">
          <span className="whitespace-pre-wrap">{body.trim()}</span>
        </ChatBubble>
        <ChatBubble from="ai" name={to.trim()}>
          <span className="whitespace-pre-wrap">{reply.reply}</span>
        </ChatBubble>
      </Card>
    );
  }

  return (
    <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Field label="받는 인물">
        {characters && characters.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {characters.map((c) => {
              const selected = to === c.name;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setTo(selected ? "" : c.name)}
                  aria-pressed={selected}
                  title={c.traits.join(", ")}
                  style={{
                    height: 38,
                    padding: "0 15px",
                    borderRadius: 999,
                    fontWeight: 700,
                    fontSize: "var(--text-sm)",
                    cursor: "pointer",
                    background: selected ? "var(--primary)" : "var(--surface-2)",
                    color: selected ? "var(--on-primary)" : "var(--text-2)",
                    border: selected
                      ? "var(--border) solid transparent"
                      : "var(--border) solid var(--line)",
                  }}
                >
                  {c.name}
                </button>
              );
            })}
          </div>
        ) : (
          <Input
            icon="user"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            placeholder="이야기 속 인물 이름"
          />
        )}
      </Field>
      <Field label="편지 내용">
        <Textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
          placeholder="하고 싶은 말을 적어 봐요."
        />
      </Field>

      {error && <ErrorText>{error}</ErrorText>}

      <Button
        icon="send"
        onClick={() => void send()}
        disabled={!to.trim() || !body.trim() || sending}
        loading={sending}
        style={{ alignSelf: "flex-start" }}
      >
        {sending ? "보내는 중…" : "편지 보내기"}
      </Button>

      {reply && reply.status === "held" && (
        <p
          className="rounded-[var(--radius-input)] bg-accent-tint p-4 font-bold"
          style={{ color: "var(--accent-text)" }}
        >
          편지를 잘 받았어요. 선생님이 확인한 뒤 답장을 줄 거예요.
        </p>
      )}
    </Card>
  );
}
