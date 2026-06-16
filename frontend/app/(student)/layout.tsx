import { AppShell } from "@/components/layout/AppShell";
import { requireRole } from "@/lib/auth/guard";

export default async function StudentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await requireRole("student");
  return <AppShell me={me}>{children}</AppShell>;
}
