import { AdminRail } from "@/components/admin/AdminRail";

/**
 * 관리자 "Control Room" 셸(new-design_version2): 좌측 아이콘 레일 + 콘텐츠 컬럼.
 * 트리 전체를 .theme-admin으로 래핑(딥네이비·mono·glow). 상단 라이브 상태바는 console/layout.
 */
export function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="theme-admin flex min-h-full flex-1">
      <AdminRail />
      <div className="flex min-w-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
