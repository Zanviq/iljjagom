"use client";

import { useEffect, useState } from "react";

import { Card } from "@/components/ui/Card";
import { getDashboardHistory } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { DashboardHistoryBucket } from "@/lib/types";

type GroupBy = "week" | "day";
type Metric = keyof Omit<DashboardHistoryBucket, "periodStart">;

const METRICS: { key: Metric; label: string }[] = [
  { key: "chaptersDone", label: "쓴 장" },
  { key: "booksFinished", label: "완독" },
  { key: "activeStudents", label: "활동 학생" },
  { key: "essaysSubmitted", label: "독후감" },
];

const GROUPS: { key: GroupBy; label: string }[] = [
  { key: "week", label: "주간" },
  { key: "day", label: "일간" },
];

/** 대시보드 과거 기록·추세(04 기능개선 교사/02 A). 미구현 시 안내(graceful). */
export function DashboardTrend({ classId }: { classId: string }) {
  const [groupBy, setGroupBy] = useState<GroupBy>("week");
  const [metric, setMetric] = useState<Metric>("chaptersDone");
  const [buckets, setBuckets] = useState<DashboardHistoryBucket[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const token = await getClientAccessToken();
        if (!active) return;
        setLoading(true);
        const { buckets: bs } = await getDashboardHistory(token, classId, groupBy);
        if (!active) return;
        setBuckets(bs);
        setUnavailable(false);
      } catch {
        if (!active) return;
        setBuckets(null);
        setUnavailable(true);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [classId, groupBy]);

  const max = buckets?.reduce((m, b) => Math.max(m, b[metric] ?? 0), 0) ?? 0;

  return (
    <Card padding="lg" className="mb-7">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[length:var(--text-md)] font-extrabold text-ink">
          활동 추세
        </h2>
        <div className="flex items-center gap-2">
          <Segment
            options={METRICS}
            value={metric}
            onChange={(v) => setMetric(v as Metric)}
          />
          <Segment
            options={GROUPS}
            value={groupBy}
            onChange={(v) => setGroupBy(v as GroupBy)}
          />
        </div>
      </div>

      {loading ? (
        <p className="text-[length:var(--text-sm)] text-ink-3">불러오는 중이에요…</p>
      ) : unavailable ? (
        <p className="text-[length:var(--text-sm)] text-ink-3">
          과거 기록을 준비하고 있어요. 조금만 기다려 주세요.
        </p>
      ) : !buckets || buckets.length === 0 ? (
        <p className="text-[length:var(--text-sm)] text-ink-3">
          아직 쌓인 기록이 없어요.
        </p>
      ) : (
        <div className="flex items-end gap-2 overflow-x-auto pb-1" style={{ height: 180 }}>
          {buckets.map((b) => {
            const v = b[metric] ?? 0;
            const h = max > 0 ? Math.round((v / max) * 140) : 0;
            return (
              <div
                key={b.periodStart}
                className="flex min-w-[34px] flex-1 flex-col items-center justify-end gap-1.5"
                title={`${shortDate(b.periodStart)} · ${v}`}
              >
                <span
                  className="font-semibold text-ink-3"
                  style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}
                >
                  {v}
                </span>
                <div
                  style={{
                    width: "100%",
                    maxWidth: 40,
                    height: Math.max(h, 2),
                    background: "var(--primary)",
                    borderRadius: "6px 6px 0 0",
                  }}
                  aria-hidden
                />
                <span
                  className="text-ink-faint"
                  style={{ fontFamily: "var(--font-mono)", fontSize: 10.5 }}
                >
                  {shortDate(b.periodStart)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function Segment({
  options,
  value,
  onChange,
}: {
  options: { key: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div
      className="inline-flex gap-0.5 rounded-[var(--radius-control)] p-0.5"
      style={{ background: "var(--surface-2)", border: "var(--border) solid var(--line)" }}
    >
      {options.map((o) => {
        const sel = o.key === value;
        return (
          <button
            key={o.key}
            type="button"
            onClick={() => onChange(o.key)}
            aria-pressed={sel}
            className="rounded-[var(--radius-control)] px-2.5 py-1 text-[length:var(--text-xs)] font-bold"
            style={{
              cursor: "pointer",
              background: sel ? "var(--primary)" : "transparent",
              color: sel ? "var(--on-primary)" : "var(--text-2)",
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getMonth() + 1}/${d.getDate()}`;
}
