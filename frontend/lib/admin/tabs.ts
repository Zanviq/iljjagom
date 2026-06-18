/** 관리자 콘솔 탭(06 §2). sessions/[id]는 상세라 탭에 없음. */
export interface ConsoleTab {
  href: string;
  label: string;
  icon: string;
}

export const CONSOLE_TABS: ConsoleTab[] = [
  { href: "/console", label: "개요", icon: "layout-dashboard" },
  { href: "/console/users", label: "사용자", icon: "users" },
  { href: "/console/sessions", label: "AI 세션", icon: "activity" },
  { href: "/console/messages", label: "대화", icon: "messages-square" },
  { href: "/console/usage", label: "토큰·비용", icon: "coins" },
  { href: "/console/safety", label: "안전", icon: "shield-alert" },
  { href: "/console/settings", label: "설정", icon: "settings-2" },
  { href: "/console/notifications", label: "알림", icon: "bell" },
  { href: "/console/backup", label: "백업", icon: "database" },
];

/** app_settings.notify_interval_sec 기본값(06 §6). 실값은 백엔드 설정에서 읽는다. */
export const DEFAULT_NOTIFY_INTERVAL_SEC = 180;
