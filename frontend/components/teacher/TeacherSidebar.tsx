"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";
import { getClassSafetyFlags, getClasses } from "@/lib/api";
import { logout } from "@/lib/auth/actions";
import { getClientAccessToken } from "@/lib/auth/client";
import { cn } from "@/lib/cn";
import type { ClassSummary, Me } from "@/lib/types";

/**
 * 교사 워크벤치 좌측 사이드바(new-design_version2 TeacherSidebar).
 * 내 학급은 항상, 학급 내부(/classes/{id}/…)에선 발제·대시보드·안전 검토를 노출.
 * 안전 검토엔 미처리 신호 수만큼 danger 배지(현재 학급 기준, best-effort).
 */
export function TeacherSidebar({ me }: { me: Me }) {
  const pathname = usePathname() || "";
  const router = useRouter();
  const classMatch = pathname.match(/^\/classes\/([^/]+)/);
  const classId = classMatch ? classMatch[1] : null;
  // 현재 학급 하위 화면(발제/대시보드/안전) — 학급 전환 시 같은 화면 유지.
  const subMatch = pathname.match(/^\/classes\/[^/]+\/([^/]+)/);
  const sub = subMatch ? subMatch[1] : "dashboard";
  const [openFlags, setOpenFlags] = useState(0);
  const [classes, setClasses] = useState<ClassSummary[]>([]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const token = await getClientAccessToken();
        const { classes: cs } = await getClasses(token);
        if (!cancelled) setClasses(cs);
      } catch {
        // 목록 실패 시 셀렉터 생략
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!classId) return;
    let cancelled = false;
    void (async () => {
      try {
        const token = await getClientAccessToken();
        const { flags } = await getClassSafetyFlags(token, classId, {
          status: "open",
        });
        if (!cancelled) setOpenFlags(flags.length);
      } catch {
        // 미구현/오류는 배지 생략
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [classId]);

  const items: {
    key: string;
    label: string;
    icon: string;
    href: string;
    active: boolean;
    badge?: number;
  }[] = [
    {
      key: "classes",
      label: "내 학급",
      icon: "layout-grid",
      href: "/classes",
      active: pathname === "/classes",
    },
  ];
  if (classId) {
    items.push(
      {
        key: "prompt",
        label: "발제",
        icon: "file-pen-line",
        href: `/classes/${classId}/prompt`,
        active: pathname.endsWith("/prompt"),
      },
      {
        key: "dashboard",
        label: "대시보드",
        icon: "chart-no-axes-column",
        href: `/classes/${classId}/dashboard`,
        active: pathname.endsWith("/dashboard"),
      },
      {
        key: "safety",
        label: "안전 검토",
        icon: "shield-check",
        href: `/classes/${classId}/safety`,
        active: pathname.endsWith("/safety"),
        badge: openFlags,
      },
      {
        key: "settings",
        label: "학급 설정",
        icon: "sliders-horizontal",
        href: `/classes/${classId}/settings`,
        active: pathname.endsWith("/settings"),
      },
    );
  }

  return (
    <aside className="sticky top-0 flex h-screen w-[248px] flex-none flex-col border-r border-line bg-surface p-4">
      <div className="flex items-center gap-2.5 px-2 pb-5 pt-1">
        <span
          className="flex h-[34px] w-[34px] items-center justify-center rounded-[9px] bg-primary text-on-primary"
          aria-hidden
        >
          <Icon name="book-heart" size={19} />
        </span>
        <div>
          <p className="ijg-wordmark text-ink" style={{ fontSize: 19, lineHeight: 1 }}>
            일짜곰
          </p>
          <p
            className="text-[length:var(--text-2xs)] font-bold text-ink-3"
            style={{ letterSpacing: ".04em" }}
          >
            교사 워크벤치
          </p>
        </div>
      </div>

      {classId && classes.length > 0 && (
        <div className="mb-3 px-1">
          <label
            className="ijg-eyebrow mb-1.5 block"
            style={{ color: "var(--text-3)" }}
            htmlFor="class-switch"
          >
            학급 선택
          </label>
          <select
            id="class-switch"
            value={classId}
            onChange={(e) => router.push(`/classes/${e.target.value}/${sub}`)}
            className="ijg-control"
            style={{ height: "var(--control-h)", padding: "0 12px", width: "100%" }}
          >
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <nav className="flex flex-col gap-0.5">
        {items.map((n) => (
          <Link
            key={n.key}
            href={n.href}
            className={cn(
              "flex items-center gap-2.5 rounded-[var(--radius-control)] px-3 py-2.5 text-[length:var(--text-sm)] font-bold transition",
              n.active
                ? "bg-primary-tint text-primary-text"
                : "text-ink-2 hover:bg-surface-inset",
            )}
          >
            <Icon name={n.icon} size={18} strokeWidth={2.25} />
            <span className="flex-1">{n.label}</span>
            {n.key === "safety" && (n.badge ?? 0) > 0 && (
              <Badge tone="danger" solid>
                {n.badge}
              </Badge>
            )}
          </Link>
        ))}
      </nav>

      <div className="mt-auto flex items-center gap-2.5 border-t border-line px-2 pt-3">
        <Avatar name={me.email} size={36} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[length:var(--text-sm)] font-bold text-ink">
            {me.email}
          </p>
        </div>
        <form action={logout}>
          <button
            type="submit"
            aria-label="로그아웃"
            className="text-ink-faint hover:text-ink-2"
          >
            <Icon name="log-out" size={17} />
          </button>
        </form>
      </div>
    </aside>
  );
}
