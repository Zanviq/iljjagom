import { Badge, type BadgeTone } from "@/components/ui/Badge";
import type { AiSessionStatus } from "@/lib/types";

const STATUS: Record<AiSessionStatus, { label: string; tone: BadgeTone }> = {
  running: { label: "동작 중", tone: "info" },
  awaiting_user: { label: "응답 대기", tone: "warning" },
  done: { label: "완료", tone: "success" },
  error: { label: "오류", tone: "danger" },
};

/** AI 세션 상태 배지(06 §3.3 색상 규약). */
export function SessionStatus({ status }: { status: AiSessionStatus }) {
  const s = STATUS[status] ?? { label: status, tone: "neutral" as BadgeTone };
  return (
    <Badge tone={s.tone} dot>
      {s.label}
    </Badge>
  );
}
