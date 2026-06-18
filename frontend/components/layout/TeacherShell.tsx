import { TeacherSidebar } from "@/components/teacher/TeacherSidebar";
import type { Me } from "@/lib/types";

/**
 * 교사 "Workbench" 셸(new-design_version2): 좌측 사이드바 + 콘텐츠.
 * 트리 전체를 .theme-teacher로 래핑(시맨틱 토큰 re-map).
 */
export function TeacherShell({
  me,
  children,
}: {
  me: Me;
  children: React.ReactNode;
}) {
  return (
    <div className="theme-teacher flex min-h-full flex-1">
      <TeacherSidebar me={me} />
      <main className="min-w-0 flex-1 px-8 py-7">
        <div className="mx-auto w-full max-w-[var(--width-content)]">
          {children}
        </div>
      </main>
    </div>
  );
}
