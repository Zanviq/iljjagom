/** 관리자 콘솔 탭(06 §2). sessions/[id]는 상세라 탭에 없음. */
export interface ConsoleTab {
  href: string;
  label: string;
}

export const CONSOLE_TABS: ConsoleTab[] = [
  { href: "/console", label: "개요" },
  { href: "/console/users", label: "사용자" },
  { href: "/console/sessions", label: "AI 세션" },
  { href: "/console/messages", label: "대화" },
  { href: "/console/usage", label: "토큰·비용" },
  { href: "/console/safety", label: "안전" },
  { href: "/console/settings", label: "설정" },
  { href: "/console/notifications", label: "알림" },
  { href: "/console/backup", label: "백업" },
];

/** app_settings.notify_interval_sec 기본값(06 §6). 실값은 백엔드 설정에서 읽는다. */
export const DEFAULT_NOTIFY_INTERVAL_SEC = 180;
