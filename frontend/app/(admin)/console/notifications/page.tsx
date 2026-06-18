import { NotificationsPanel } from "@/components/admin/NotificationsPanel";
import { ErrorText } from "@/components/ui/ErrorText";
import { getAdminNotifications } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { AppNotification } from "@/lib/types";

export default async function ConsoleNotificationsPage() {
  const token = await getAccessToken();
  let notifications: AppNotification[] = [];
  let error: string | null = null;
  try {
    ({ notifications } = await getAdminNotifications(token, { limit: 50 }));
  } catch (e) {
    error = e instanceof Error ? e.message : "알림을 불러오지 못했어요.";
  }

  return (
    <div>
      <p className="ijg-eyebrow mb-4 text-ink-3">
        알림 · 사용자/역할/전체에 보내고 수신함 보기
      </p>
      {error ? (
        <ErrorText className="mt-2">{error}</ErrorText>
      ) : (
        <NotificationsPanel notifications={notifications} />
      )}
    </div>
  );
}
