import { ConsoleHeader } from "@/components/admin/ConsoleHeader";
import { getAdminSettings, getHealth } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import { DEFAULT_NOTIFY_INTERVAL_SEC } from "@/lib/admin/tabs";
import type { Health } from "@/lib/types";

/**
 * 콘솔 셸: 상단 라이브 상태바 + 본문. 좌측 탭 내비는 AdminShell 아이콘 레일이 담당.
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
    <>
      <ConsoleHeader health={health} intervalSec={intervalSec} />
      <div className="px-7 py-6">{children}</div>
    </>
  );
}
