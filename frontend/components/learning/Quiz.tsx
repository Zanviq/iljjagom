"use client";

import { useEffect, useRef, useState } from "react";

import { Card } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { postLearningResult } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import { cn } from "@/lib/cn";
import type { QuizItem } from "@/lib/types";

/**
 * 퀴즈. 모든 문항을 답하면 결과를 1회 저장(추가기능 04: learning-results type=quiz).
 * 저장 실패는 학습 흐름을 막지 않는다(조용히 무시).
 */
export function Quiz({ items, bookId }: { items: QuizItem[]; bookId: string }) {
  const [picked, setPicked] = useState<(number | null)[]>(() =>
    items.map(() => null),
  );
  // 1회만 저장(상태 대신 ref — effect 내 setState 회피).
  const savedRef = useRef(false);

  useEffect(() => {
    if (savedRef.current || items.length === 0) return;
    if (!picked.every((p) => p !== null)) return;
    savedRef.current = true;
    const answers = picked.map((p, i) => ({
      index: i,
      picked: p,
      correct: p === items[i].answerIndex,
    }));
    const data = {
      answers,
      score: answers.filter((a) => a.correct).length,
      total: items.length,
    };
    void (async () => {
      try {
        const token = await getClientAccessToken();
        await postLearningResult(token, bookId, { type: "quiz", data });
      } catch {
        // 측정 실패 무시
      }
    })();
  }, [picked, items, bookId]);

  return (
    <div className="flex flex-col gap-4">
      {items.map((q, i) => (
        <QuizCard
          key={i}
          item={q}
          index={i}
          picked={picked[i]}
          onPick={(c) =>
            setPicked((prev) => {
              const next = [...prev];
              next[i] = c;
              return next;
            })
          }
        />
      ))}
    </div>
  );
}

function QuizCard({
  item,
  index,
  picked,
  onPick,
}: {
  item: QuizItem;
  index: number;
  picked: number | null;
  onPick: (choice: number | null) => void;
}) {
  const answered = picked !== null;
  const correct = picked === item.answerIndex;

  return (
    <Card padding="lg">
      <p className="mb-3 font-bold text-ink" style={{ fontSize: 17 }}>
        {index + 1}. {item.question}
      </p>
      <div className="flex flex-col gap-2.5">
        {item.choices.map((choice, ci) => {
          const isAnswer = ci === item.answerIndex;
          const isPicked = ci === picked;
          return (
            <button
              key={ci}
              onClick={() => onPick(ci)}
              disabled={answered}
              className={cn(
                "flex w-full items-center justify-between gap-2.5 rounded-[var(--radius-input)] border-2 px-4 py-3 text-left font-semibold transition disabled:cursor-default",
                !answered &&
                  "border-line-strong bg-surface-2 text-ink hover:border-primary",
                answered &&
                  isAnswer &&
                  "border-success bg-success-tint text-success-text",
                answered &&
                  isPicked &&
                  !isAnswer &&
                  "border-danger bg-danger-tint text-danger-text",
                answered &&
                  !isAnswer &&
                  !isPicked &&
                  "border-line-strong bg-surface-2 text-ink opacity-60",
              )}
            >
              {choice}
              {answered && isAnswer && <Icon name="check" size={18} strokeWidth={3} />}
              {answered && isPicked && !isAnswer && (
                <Icon name="x" size={18} strokeWidth={3} />
              )}
            </button>
          );
        })}
      </div>
      {answered && (
        <p
          className="mt-2.5 text-[length:var(--text-sm)] font-bold"
          style={{
            color: correct ? "var(--success-text)" : "var(--danger-text)",
          }}
        >
          {correct ? "정답이에요! 잘했어요." : "다시 한 번 생각해 볼까요?"}
          {!correct && (
            <button onClick={() => onPick(null)} className="ml-2 underline">
              다시 풀기
            </button>
          )}
        </p>
      )}
    </Card>
  );
}
