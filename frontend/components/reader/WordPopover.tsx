"use client";

import { useEffect, useRef } from "react";

import { buttonClass } from "@/components/ui/Button";
import { Loading } from "@/components/ui/Loading";
import type { Word } from "@/lib/types";

/**
 * 단어 도움 팝오버(FR-S7). 발음/뜻을 보여 준다.
 * 접근성: role="dialog" aria-modal, Esc로 닫기, 열리면 닫기 버튼에 포커스 이동·닫으면 이전 포커스 복원.
 */
export function WordPopover({
  word,
  loading,
  onClose,
}: {
  word: Word | null;
  loading: boolean;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    // 열릴 때 이전 포커스를 기억하고 닫기 버튼으로 이동, 닫힐 때 복원.
    const prev = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      prev?.focus?.();
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-20 flex items-end justify-center bg-black/30 p-4 sm:items-center"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={word ? `낱말 뜻: ${word.term}` : "낱말 뜻"}
        className="w-full max-w-sm rounded-card bg-surface p-6 shadow-lg ring-1 ring-border"
        onClick={(e) => e.stopPropagation()}
      >
        {loading || !word ? (
          <Loading>낱말을 찾는 중…</Loading>
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
          ref={closeRef}
          onClick={onClose}
          className={buttonClass("primary", "md", "mt-5 w-full")}
        >
          알았어요
        </button>
      </div>
    </div>
  );
}
