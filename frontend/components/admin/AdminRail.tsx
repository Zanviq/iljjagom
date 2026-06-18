"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon } from "@/components/ui/Icon";
import { CONSOLE_TABS } from "@/lib/admin/tabs";
import { logout } from "@/lib/auth/actions";
import { cn } from "@/lib/cn";

/**
 * 관리자 "Control Room" 좌측 아이콘 레일(new-design_version2 AdminRail).
 * 콘솔 9탭을 아이콘+라벨로. 로고 타일은 glow-cyan, 하단은 로그아웃.
 */
export function AdminRail() {
  const pathname = usePathname() || "";

  return (
    <aside className="sticky top-0 flex h-screen w-[76px] flex-none flex-col items-center gap-1.5 border-r border-line bg-surface py-[18px]">
      <span
        className="mb-3.5 flex h-10 w-10 items-center justify-center rounded-[11px] bg-primary text-on-primary"
        style={{ boxShadow: "var(--glow-cyan)" }}
        aria-hidden
      >
        <Icon name="book-heart" size={22} />
      </span>

      <nav className="flex flex-1 flex-col items-center gap-1.5">
        {CONSOLE_TABS.map((tab) => {
          const active =
            tab.href === "/console"
              ? pathname === "/console"
              : pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              title={tab.label}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex w-[60px] flex-col items-center gap-1 rounded-[10px] py-2.5 text-[10.5px] font-bold transition",
                active
                  ? "bg-primary-tint text-primary"
                  : "text-ink-3 hover:bg-surface-inset",
              )}
            >
              <Icon name={tab.icon} size={20} strokeWidth={2} />
              {tab.label}
            </Link>
          );
        })}
      </nav>

      <form action={logout} className="mt-auto">
        <button
          type="submit"
          aria-label="로그아웃"
          title="로그아웃"
          className="flex w-[60px] flex-col items-center gap-1 rounded-[10px] py-2.5 text-[10.5px] font-bold text-ink-3 hover:bg-surface-inset"
        >
          <Icon name="log-out" size={20} strokeWidth={2} />
          로그아웃
        </button>
      </form>
    </aside>
  );
}

/** 라이브 신호 점(맥동). 관리자 상단바·세션 카드에 사용. */
export function LiveDot({ color = "var(--primary)" }: { color?: string }) {
  return (
    <span
      aria-hidden
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: 999,
        background: color,
        boxShadow: `0 0 8px ${color}`,
        animation: "ijg-pulse 1.6s var(--ease-in-out) infinite",
      }}
    />
  );
}
