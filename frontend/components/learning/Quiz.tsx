"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";
import type { QuizItem } from "@/lib/types";

export function Quiz({ items }: { items: QuizItem[] }) {
  return (
    <ul className="space-y-4">
      {items.map((q, i) => (
        <QuizCard key={i} item={q} index={i} />
      ))}
    </ul>
  );
}

function QuizCard({ item, index }: { item: QuizItem; index: number }) {
  const [picked, setPicked] = useState<number | null>(null);
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
                onClick={() => setPicked(ci)}
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
            <button
              onClick={() => setPicked(null)}
              className="ml-2 underline"
            >
              다시 풀기
            </button>
          )}
        </p>
      )}
    </li>
  );
}
