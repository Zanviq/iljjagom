"use client";

import { useEffect, useRef } from "react";

import { buttonClass } from "@/components/ui/Button";

/**
 * 위험 액션 확인 모달(06: 역할 변경·비활성·복원 등). 접근성: dialog·Esc·포커스 이동.
 * 데이터 바인딩 후 각 위험 액션에서 재사용한다(지금은 프리미티브만 제공).
 */
export function ConfirmModal({
  title,
  body,
  confirmLabel = "확인",
  danger = true,
  onConfirm,
  onCancel,
  pending = false,
}: {
  title: string;
  body: React.ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  pending?: boolean;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      prev?.focus?.();
    };
  }, [onCancel]);

  return (
    <div
      className="fixed inset-0 z-30 flex items-end justify-center bg-black/40 p-4 sm:items-center"
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-md rounded-card bg-surface p-6 shadow-lg ring-1 ring-border"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-extrabold">{title}</h2>
        <div className="mt-2 text-muted">{body}</div>
        <div className="mt-5 flex gap-2">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className={buttonClass("ghost", "md", "flex-1")}
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            disabled={pending}
            className={buttonClass(danger ? "danger" : "primary", "md", "flex-1")}
          >
            {pending ? "처리 중…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
