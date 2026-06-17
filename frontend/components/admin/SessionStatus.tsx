import { cn } from "@/lib/cn";
import type { AiSessionStatus } from "@/lib/types";

const STATUS: Record<AiSessionStatus, { label: string; cls: string }> = {
  running: { label: "동작 중", cls: "bg-secondary/15 text-secondary-strong" },
  awaiting_user: { label: "응답 대기", cls: "bg-accent/50 text-foreground" },
  done: { label: "완료", cls: "bg-success/15 text-success-strong" },
  error: { label: "오류", cls: "bg-danger/10 text-danger" },
};

/** AI 세션 상태 배지(06 §3.3 색상 규약). */
export function SessionStatus({ status }: { status: AiSessionStatus }) {
  const s = STATUS[status] ?? { label: status, cls: "bg-black/5 text-muted" };
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-sm font-bold", s.cls)}>
      {s.label}
    </span>
  );
}
