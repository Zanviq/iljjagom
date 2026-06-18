import { TeacherShell } from "@/components/layout/TeacherShell";
import { requireRole } from "@/lib/auth/guard";

export default async function TeacherLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await requireRole("teacher");
  return <TeacherShell me={me}>{children}</TeacherShell>;
}
