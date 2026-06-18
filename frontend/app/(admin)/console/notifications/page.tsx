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
      <h1 className="text-3xl font-extrabold">알림</h1>
      <p className="mt-1 text-muted">
        사용자/역할/전체에 알림을 보내고 수신함을 봐요.
      </p>
      {error ? (
        <ErrorText className="mt-6">{error}</ErrorText>
      ) : (
        <div className="mt-6">
          <NotificationsPanel notifications={notifications} />
        </div>
      )}
    </div>
  );
}
