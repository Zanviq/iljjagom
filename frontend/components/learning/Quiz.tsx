"use client";

import { useEffect, useRef, useState } from "react";

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
    <ul className="space-y-4">
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
    </ul>
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
    <li className="rounded-card bg-surface p-5 ring-1 ring-border">
      <p className="font-bold">
        {index + 1}. {item.question}
      </p>
      <ul className="mt-3 space-y-2">
        {item.choices.map((choice, ci) => {
          const isAnswer = ci === item.answerIndex;
          const isPicked = ci === picked;
          return (
            <li key={ci}>
              <button
                onClick={() => onPick(ci)}
                disabled={answered}
                className={cn(
                  "w-full rounded-xl border-2 px-4 py-2.5 text-left text-lg transition disabled:cursor-default",
                  !answered && "border-border bg-background hover:border-primary",
                  answered && isAnswer && "border-success bg-success/15 font-bold",
                  answered &&
                    isPicked &&
                    !isAnswer &&
                    "border-danger bg-danger/10",
                  answered && !isAnswer && !isPicked && "border-border opacity-60",
                )}
              >
                {choice}
                {answered && isAnswer && " ✓"}
              </button>
            </li>
          );
        })}
      </ul>
      {answered && (
        <p
          className={cn(
            "mt-3 text-sm font-bold",
            correct ? "text-success-strong" : "text-danger",
          )}
        >
          {correct ? "정답이에요! 🎉" : "다시 한 번 생각해 볼까요?"}
          {!correct && (
            <button onClick={() => onPick(null)} className="ml-2 underline">
              다시 풀기
            </button>
          )}
        </p>
      )}
    </li>
  );
}
