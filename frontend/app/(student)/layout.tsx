import { StudentShell } from "@/components/layout/StudentShell";
import { requireRole } from "@/lib/auth/guard";

export default async function StudentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await requireRole("student");
  return <StudentShell me={me}>{children}</StudentShell>;
}
