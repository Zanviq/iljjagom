import { cn } from "@/lib/cn";
import type { SafetyFlag } from "@/lib/types";

/** 안전 신호 심각도 배지(severity 문자열 기반, 미지정값은 중립). */
export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    high: "bg-danger/10 text-danger",
    med: "bg-accent/50 text-foreground",
    medium: "bg-accent/50 text-foreground",
    low: "bg-black/5 text-muted",
  };
  return (
    <span
      className={cn(
        "rounded-full px-2.5 py-0.5 text-xs font-bold",
        map[severity] ?? "bg-black/5 text-muted",
      )}
    >
      {severity}
    </span>
  );
}

function fmt(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString("ko-KR");
}

/** 안전 신호 읽기 전용 목록(관리자 콘솔 드릴다운용). 카드 스타일. */
export function SafetyFlagList({ flags }: { flags: SafetyFlag[] }) {
  return (
    <ul className="space-y-3">
      {flags.map((f) => (
        <li key={f.id} className="rounded-card bg-surface p-4 ring-1 ring-border">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={f.severity} />
            <span className="rounded-full bg-black/5 px-2.5 py-0.5 text-xs font-bold text-muted">
              {f.source}
            </span>
            {f.category && (
              <span className="rounded-full bg-black/5 px-2.5 py-0.5 text-xs font-bold text-muted">
                {f.category}
              </span>
            )}
            <span
              className={cn(
                "ml-auto rounded-full px-2.5 py-0.5 text-xs font-bold",
                f.status === "open"
                  ? "bg-danger/10 text-danger"
                  : "bg-success/15 text-success-strong",
              )}
            >
              {f.status === "open" ? "미처리" : "종결"}
            </span>
          </div>
          <p className="mt-2 text-sm">{f.reason}</p>
          <p className="mt-1 text-xs text-muted">{fmt(f.createdAt)}</p>
        </li>
      ))}
    </ul>
  );
}
