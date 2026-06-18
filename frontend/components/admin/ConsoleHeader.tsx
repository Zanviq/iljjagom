"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";
import type { Health } from "@/lib/types";

/**
 * 콘솔 상단 바: 백엔드 모드 배지(/health storage·ai) + 실시간 갱신 토글(06 §2).
 * 실시간 주기는 app_settings.notify_interval_sec(기본 180s) — 계약 확정 후 각 탭이
 * 이 토글 상태를 구독해 폴링한다. 지금은 토글 UI·주기 표시까지(데이터 바인딩 후속).
 */
export function ConsoleHeader({
  health,
  intervalSec,
}: {
  health: Health | null;
  intervalSec: number;
}) {
  const [live, setLive] = useState(false);

  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {health ? (
          <>
            <Badge
              label={`저장소 ${health.storage}`}
              tone={health.storage === "supabase" ? "ok" : "warn"}
            />
            <Badge
              label={`AI ${health.ai}`}
              tone={health.ai === "google" ? "ok" : "warn"}
            />
            <Badge label={`env ${health.env}`} tone="neutral" />
          </>
        ) : (
          <Badge label="백엔드 연결 안 됨" tone="danger" />
        )}
      </div>

      <label className="flex items-center gap-2 text-sm font-bold">
        <input
          type="checkbox"
          checked={live}
          onChange={(e) => setLive(e.target.checked)}
          className="h-5 w-5 accent-[var(--primary)]"
        />
        실시간 갱신
        <span className="font-normal text-muted">({intervalSec}초)</span>
      </label>
    </div>
  );
}

function Badge({
  label,
  tone,
}: {
  label: string;
  tone: "ok" | "warn" | "neutral" | "danger";
}) {
  const tones: Record<typeof tone, string> = {
    ok: "bg-success/15 text-success-strong",
    warn: "bg-accent/40 text-foreground",
    neutral: "bg-black/5 text-muted",
    danger: "bg-danger/10 text-danger",
  };
  return (
    <span className={cn("rounded-full px-3 py-1 font-bold", tones[tone])}>
      {label}
    </span>
  );
}
