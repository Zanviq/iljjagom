import { ConsoleHeader } from "@/components/admin/ConsoleHeader";
import { ConsoleNav } from "@/components/admin/ConsoleNav";
import { getHealth } from "@/lib/api";
import { DEFAULT_NOTIFY_INTERVAL_SEC } from "@/lib/admin/tabs";
import type { Health } from "@/lib/types";

/**
 * 콘솔 공통 셸: 상단 모드 배지·실시간 토글 + 탭 바. (admin) 게이트(layout)가 관리자만 통과시킨다.
 * 실시간 주기는 app_settings.notify_interval_sec(계약 확정 후) — 지금은 기본 180s.
 */
export default async function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const health: Health | null = await getHealth().catch(() => null);

  return (
    <div>
      <ConsoleHeader
        health={health}
        intervalSec={DEFAULT_NOTIFY_INTERVAL_SEC}
      />
      <ConsoleNav />
      {children}
    </div>
  );
}
