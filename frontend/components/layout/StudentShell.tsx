import Link from "next/link";

import { AiAssistant } from "@/components/ai/AiAssistant";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { logout } from "@/lib/auth/actions";
import type { Me } from "@/lib/types";

/**
 * 학생 "Reading Room" 셸(new-design_version2 StudentShell).
 * 상단바(워드마크 + 학급 배지 + 아바타 + 로그아웃). 본문은 화면별 컨테이너가 폭/여백을 가짐.
 * AI FAB/드로어(곰 작가)는 04 단계에서 추가(메인에서만 노출).
 */
export function StudentShell({
  me,
  children,
}: {
  me: Me;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header
        className="sticky top-0 z-20 border-b border-line"
        style={{
          background: "color-mix(in oklab, var(--surface) 86%, transparent)",
          backdropFilter: "blur(10px)",
        }}
      >
        <div className="mx-auto flex w-full max-w-[var(--width-content)] items-center justify-between gap-4 px-6 py-3">
          <Link href="/home" className="flex items-center gap-2.5">
            <span
              className="flex h-[38px] w-[38px] items-center justify-center rounded-xl bg-primary text-on-primary shadow-[var(--elev-sm)]"
              aria-hidden
            >
              <Icon name="book-heart" size={21} strokeWidth={2.25} />
            </span>
            <span
              className="ijg-wordmark text-ink"
              style={{ fontSize: 24 }}
            >
              일짜곰
            </span>
          </Link>
          <div className="flex items-center gap-3">
            {me.className && (
              <Badge tone="accent" icon="school">
                {me.className}
              </Badge>
            )}
            <Avatar name={me.email} size={34} />
            <form action={logout}>
              <Button type="submit" variant="ghost" size="sm" icon="log-out">
                로그아웃
              </Button>
            </form>
          </div>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <AiAssistant />
    </div>
  );
}
