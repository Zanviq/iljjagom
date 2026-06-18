import { ConsoleHeader } from "@/components/admin/ConsoleHeader";
import { ConsoleNav } from "@/components/admin/ConsoleNav";
import { getAdminSettings, getHealth } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import { DEFAULT_NOTIFY_INTERVAL_SEC } from "@/lib/admin/tabs";
import type { Health } from "@/lib/types";

/**
 * 콘솔 공통 셸: 상단 모드 배지·실시간 토글 + 탭 바. (admin) 게이트(layout)가 관리자만 통과시킨다.
 * 실시간 주기는 app_settings.notify_interval_sec(없으면 기본 180s).
 */
export default async function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const token = await getAccessToken();
  const [health, settings] = await Promise.all([
    getHealth().catch((): Health | null => null),
    getAdminSettings(token).catch(() => null),
  ]);

  const raw = settings?.settings?.notify_interval_sec;
  const intervalSec =
    typeof raw === "number" && raw > 0 ? raw : DEFAULT_NOTIFY_INTERVAL_SEC;

  return (
    <div>
      <ConsoleHeader health={health} intervalSec={intervalSec} />
      <ConsoleNav />
      {children}
    </div>
  );
}
