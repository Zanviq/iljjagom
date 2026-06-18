import { AppShell } from "@/components/layout/AppShell";
import { requireRole } from "@/lib/auth/guard";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await requireRole("admin");
  return (
    <div className="theme-admin flex min-h-full flex-1 flex-col">
      <AppShell me={me}>{children}</AppShell>
    </div>
  );
}
