"use client";

import { useId, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ErrorText } from "@/components/ui/ErrorText";
import { Icon } from "@/components/ui/Icon";
import { Textarea } from "@/components/ui/Textarea";
import { cn } from "@/lib/cn";
import type { AskUserAnswer, AskUserPrompt } from "@/lib/ai";

/**
 * 클로드식 질문 칸: AI가 흐름 도중 물어보면 질문 + 선택지 버튼 + (허용 시) 직접 입력을 렌더하고,
 * 아이가 고르거나 적으면 onAnswer로 응답을 올려 흐름을 재개한다. (02 ask_user)
 * - 프리젠테이션 컴포넌트: 질문 노출 경로(SSE/폴링)와 무관하게 재사용.
 * - 접근성: role="group" + aria-label, 선택지는 라디오 의미(aria-pressed), 직접 입력은 라벨 연결.
 */
export function AskUserPanel({
  prompt,
  pending = false,
  error,
  onAnswer,
}: {
  prompt: AskUserPrompt;
  pending?: boolean;
  error?: string | null;
  onAnswer: (answer: AskUserAnswer) => void;
}) {
  const [picked, setPicked] = useState<number | null>(null);
  const [text, setText] = useState("");
  const textId = useId();

  const trimmed = text.trim();
  // 선택지를 고른 상태이거나(직접입력 비었음), 직접입력에 내용이 있으면 보낼 수 있다.
  const canSend =
    !pending &&
    ((picked !== null && trimmed.length === 0) || trimmed.length > 0);

  function submit() {
    if (!canSend) return;
    // 계약(AnswerRequest)은 choice가 선택지 "값 문자열"이다(인덱스 아님).
    if (trimmed.length > 0) onAnswer({ text: trimmed });
    else if (picked !== null) onAnswer({ choice: prompt.choices[picked] });
  }

  return (
    <section
      role="group"
      aria-label="이야기 친구의 질문"
      className="rounded-[var(--radius-card)] bg-surface p-5"
      style={{ border: "2px solid color-mix(in oklab, var(--primary) 45%, transparent)" }}
    >
      <p className="flex items-start gap-2 text-[length:var(--text-md)] font-bold text-ink">
        <Icon name="message-circle" size={20} style={{ color: "var(--primary)" }} />
        <span>{prompt.question}</span>
      </p>

      {prompt.choices.length > 0 && (
        <div className="mt-4 flex flex-col gap-2">
          {prompt.choices.map((choice, i) => {
            const active = picked === i && trimmed.length === 0;
            return (
              <button
                key={i}
                type="button"
                aria-pressed={active}
                disabled={pending}
                onClick={() => {
                  setPicked(i);
                  setText("");
                }}
                className={cn(
                  "rounded-[var(--radius-input)] border-2 px-4 py-3 text-left text-[length:var(--text-md)] font-bold transition disabled:opacity-50",
                  active
                    ? "border-primary bg-primary-tint text-ink"
                    : "border-line-strong bg-surface-2 hover:border-primary",
                )}
              >
                {choice}
              </button>
            );
          })}
        </div>
      )}

      {prompt.allowText && (
        <div className="mt-4">
          <label
            htmlFor={textId}
            className="mb-1 block text-[length:var(--text-sm)] font-bold text-ink-2"
          >
            {prompt.choices.length > 0 ? "아니면 직접 적어볼래?" : "여기에 적어줘"}
          </label>
          <Textarea
            id={textId}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              if (e.target.value.trim().length > 0) setPicked(null);
            }}
            rows={2}
            disabled={pending}
            placeholder="내 생각을 적어줘…"
          />
        </div>
      )}

      {error && <ErrorText className="mt-3">{error}</ErrorText>}

      <Button
        type="button"
        onClick={submit}
        disabled={!canSend}
        fullWidth
        loading={pending}
        className="mt-4"
      >
        {pending ? "전하는 중…" : "이걸로 할래!"}
      </Button>
    </section>
  );
}
