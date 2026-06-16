import { AppShell } from "@/components/layout/AppShell";
import { requireRole } from "@/lib/auth/guard";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await requireRole("admin");
  return <AppShell me={me}>{children}</AppShell>;
}
