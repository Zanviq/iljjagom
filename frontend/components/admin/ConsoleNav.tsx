"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { CONSOLE_TABS } from "@/lib/admin/tabs";
import { cn } from "@/lib/cn";

/** 콘솔 탭 바(가로 스크롤·활성 강조). sessions 상세도 'AI 세션' 활성 처리. */
export function ConsoleNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="관리자 콘솔 탭"
      className="-mx-1 mb-6 flex gap-1 overflow-x-auto border-b border-border pb-px"
    >
      {CONSOLE_TABS.map((tab) => {
        const active =
          tab.href === "/console"
            ? pathname === "/console"
            : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "-mb-px whitespace-nowrap border-b-2 px-4 py-2 text-sm font-bold transition",
              active
                ? "border-primary text-primary-strong"
                : "border-transparent text-muted hover:bg-black/5",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
