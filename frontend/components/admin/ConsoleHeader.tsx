"use client";

import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { LiveDot } from "@/components/admin/AdminRail";
import { CONSOLE_TABS } from "@/lib/admin/tabs";
import type { Health } from "@/lib/types";

/**
 * 관리자 "Control Room" 상단 라이브 상태바(new-design_version2 AdminTopBar).
 * 제목(현재 탭) + 관제 콘솔 + 백엔드 모드 배지(/health) + SYSTEMS NOMINAL + 시계 + 실시간 토글(06 §2).
 * 토글 ON 시 주기(app_settings.notify_interval_sec, 기본 180s)마다 router.refresh().
 */
export function ConsoleHeader({
  health,
  intervalSec,
}: {
  health: Health | null;
  intervalSec: number;
}) {
  const router = useRouter();
  const pathname = usePathname() || "";
  const [live, setLive] = useState(false);
  const [clock, setClock] = useState("--:--:--");

  useEffect(() => {
    const tick = () => setClock(new Date().toTimeString().slice(0, 8));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!live) return;
    const ms = Math.max(10, intervalSec) * 1000;
    const id = setInterval(() => router.refresh(), ms);
    return () => clearInterval(id);
  }, [live, intervalSec, router]);

  const tab =
    [...CONSOLE_TABS]
      .filter((t) =>
        t.href === "/console" ? pathname === "/console" : pathname.startsWith(t.href),
      )
      .sort((a, b) => b.href.length - a.href.length)[0] ?? CONSOLE_TABS[0];

  return (
    <header className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 border-b border-line bg-bg-tint px-7 py-4">
      <div className="flex items-center gap-3">
        <h1 className="text-[length:var(--text-md)] font-extrabold text-ink">
          {tab.label}
        </h1>
        <span
          className="text-ink-3"
          style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: ".08em" }}
        >
          관제 콘솔
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        {health ? (
          <span
            className="text-ink-3"
            style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: ".05em" }}
          >
            STORAGE {health.storage.toUpperCase()} · AI {health.ai.toUpperCase()} ·{" "}
            {health.env.toUpperCase()}
          </span>
        ) : (
          <span
            style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--danger-text)" }}
          >
            BACKEND OFFLINE
          </span>
        )}

        <span
          className="inline-flex items-center gap-1.5"
          style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--success-text)" }}
        >
          <LiveDot color="var(--success)" /> SYSTEMS NOMINAL
        </span>

        <span
          className="text-ink-2"
          style={{ fontFamily: "var(--font-mono)", fontSize: 13, letterSpacing: ".05em" }}
        >
          {clock}
        </span>

        <label className="inline-flex items-center gap-2 text-[length:var(--text-sm)] font-bold text-ink">
          <input
            type="checkbox"
            checked={live}
            onChange={(e) => setLive(e.target.checked)}
            className="h-4 w-4 accent-[var(--primary)]"
          />
          실시간
          <span className="font-normal text-ink-3">({intervalSec}s)</span>
        </label>
      </div>
    </header>
  );
}
