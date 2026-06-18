import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type { SafetyFlag } from "@/lib/types";

/** 안전 신호 심각도 배지(severity 문자열 기반, 미지정값은 중립). */
export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, BadgeTone> = {
    high: "danger",
    med: "warning",
    medium: "warning",
    low: "neutral",
  };
  return <Badge tone={map[severity] ?? "neutral"}>{severity}</Badge>;
}

function fmt(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString("ko-KR");
}

/** 안전 신호 읽기 전용 목록(관리자 콘솔 드릴다운용). 카드 스타일. */
export function SafetyFlagList({ flags }: { flags: SafetyFlag[] }) {
  return (
    <div className="flex flex-col gap-3">
      {flags.map((f) => (
        <Card key={f.id} padding="md">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={f.severity} />
            <Badge tone="neutral">{f.source}</Badge>
            {f.category && <Badge tone="neutral">{f.category}</Badge>}
            <span className="ml-auto">
              <Badge tone={f.status === "open" ? "danger" : "success"}>
                {f.status === "open" ? "미처리" : "종결"}
              </Badge>
            </span>
          </div>
          <p className="mt-2 text-[length:var(--text-sm)] text-ink">{f.reason}</p>
          <p className="mt-1 text-[length:var(--text-xs)] text-ink-3">
            {fmt(f.createdAt)}
          </p>
        </Card>
      ))}
    </div>
  );
}
