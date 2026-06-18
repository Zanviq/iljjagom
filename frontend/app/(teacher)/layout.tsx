import { AppShell } from "@/components/layout/AppShell";
import { requireRole } from "@/lib/auth/guard";

export default async function TeacherLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await requireRole("teacher");
  return (
    <div className="theme-teacher flex min-h-full flex-1 flex-col">
      <AppShell me={me}>{children}</AppShell>
    </div>
  );
}
