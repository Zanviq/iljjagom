import { Pending } from "@/components/admin/Pending";

export default function ConsoleNotificationsPage() {
  return (
    <Pending
      title="알림"
      describe="관리자/사용자에게 알림을 보내고 수신함을 봐요. 자동 알림(안전·오류·정체·예산)은 주기적으로 점검됩니다."
      endpoint="GET/POST /admin/notifications"
    />
  );
}
