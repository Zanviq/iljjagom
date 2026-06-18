import { AdminShell } from "@/components/layout/AdminShell";
import { requireRole } from "@/lib/auth/guard";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await requireRole("admin");
  return <AdminShell>{children}</AdminShell>;
}
