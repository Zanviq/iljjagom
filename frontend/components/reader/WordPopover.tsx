"use client";

import type { Word } from "@/lib/types";

/** 단어 도움 팝오버(FR-S7). 발음/뜻을 보여 준다. */
export function WordPopover({
  word,
  loading,
  onClose,
}: {
  word: Word | null;
  loading: boolean;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-20 flex items-end justify-center bg-black/30 p-4 sm:items-center"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-card bg-surface p-6 shadow-lg ring-1 ring-border"
        onClick={(e) => e.stopPropagation()}
      >
        {loading || !word ? (
          <p className="text-muted">낱말을 찾는 중…</p>
        ) : (
          <>
            <p className="text-2xl font-extrabold">{word.term}</p>
            {word.reading && word.reading !== word.term && (
              <p className="mt-1 text-lg text-muted">[{word.reading}]</p>
            )}
            <p className="mt-3 text-lg">{word.meaning}</p>
          </>
        )}
        <button
          onClick={onClose}
          className="mt-5 w-full rounded-card bg-primary px-4 py-2 font-bold text-primary-foreground"
        >
          알았어요
        </button>
      </div>
    </div>
  );
}
