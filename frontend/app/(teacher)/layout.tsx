import { AppShell } from "@/components/layout/AppShell";
import { requireRole } from "@/lib/auth/guard";

export default async function TeacherLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await requireRole("teacher");
  return <AppShell me={me}>{children}</AppShell>;
}
