import Link from "next/link";

import { logout } from "@/lib/auth/actions";
import { roleHome } from "@/lib/auth/guard";
import { cn } from "@/lib/cn";
import type { Me } from "@/lib/types";

const ROLE_LABEL: Record<Me["role"], string> = {
  student: "학생",
  teacher: "교사",
  admin: "관리자",
};

/** 역할 셸: 상단 바(브랜드/역할/로그아웃) + 본문. */
export function AppShell({
  me,
  children,
  className,
}: {
  me: Me;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="sticky top-0 z-10 border-b border-border bg-surface/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-5 py-3">
          <Link href={roleHome(me.role)} className="text-xl font-extrabold">
            🐻 일짜곰
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-muted sm:inline">{me.email}</span>
            <span className="rounded-full bg-accent/40 px-3 py-1 font-bold">
              {ROLE_LABEL[me.role]}
            </span>
            <form action={logout}>
              <button
                type="submit"
                className="rounded-full px-3 py-1 font-bold text-muted hover:bg-black/5"
              >
                로그아웃
              </button>
            </form>
          </div>
        </div>
      </header>
      <main className={cn("mx-auto w-full max-w-5xl flex-1 px-5 py-8", className)}>
        {children}
      </main>
    </div>
  );
}
