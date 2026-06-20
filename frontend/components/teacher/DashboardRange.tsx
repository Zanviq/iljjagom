"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/Button";

/**
 * 대시보드 기간 필터(04 기능개선 교사/02 A). 지표 집계 범위를 from/to 로 좁힌다.
 * URL 쿼리(?from=&to=)를 갱신 → 서버 컴포넌트가 해당 범위로 다시 집계한다.
 */
export function DashboardRange({ from, to }: { from?: string; to?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  function apply(next: { from?: string; to?: string }) {
    const sp = new URLSearchParams(params.toString());
    if (next.from) sp.set("from", next.from);
    else sp.delete("from");
    if (next.to) sp.set("to", next.to);
    else sp.delete("to");
    const qs = sp.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  const active = Boolean(from || to);

  return (
    <div className="mb-3.5 flex flex-wrap items-end gap-2.5">
      <label className="flex flex-col gap-1">
        <span className="ijg-eyebrow text-ink-3">시작일</span>
        <input
          type="date"
          defaultValue={from ?? ""}
          max={to || undefined}
          onChange={(e) => apply({ from: e.target.value, to })}
          className="ijg-control rounded-[var(--radius-input)] border border-line bg-surface px-3 text-[length:var(--text-sm)] text-ink"
          style={{ height: "var(--control-h)" }}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="ijg-eyebrow text-ink-3">종료일</span>
        <input
          type="date"
          defaultValue={to ?? ""}
          min={from || undefined}
          onChange={(e) => apply({ from, to: e.target.value })}
          className="ijg-control rounded-[var(--radius-input)] border border-line bg-surface px-3 text-[length:var(--text-sm)] text-ink"
          style={{ height: "var(--control-h)" }}
        />
      </label>
      {active && (
        <Button variant="ghost" size="sm" icon="x" onClick={() => apply({})}>
          기간 해제
        </Button>
      )}
    </div>
  );
}
