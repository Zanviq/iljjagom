import { UsersTable } from "@/components/admin/UsersTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
import { getAdminUsers } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { AdminUser } from "@/lib/types";

export default async function ConsoleUsersPage() {
  const token = await getAccessToken();
  let users: AdminUser[] | null = null;
  let error: string | null = null;
  try {
    ({ users } = await getAdminUsers(token));
  } catch (e) {
    error = e instanceof Error ? e.message : "사용자를 불러오지 못했어요.";
  }

  return (
    <div>
      <p className="ijg-eyebrow mb-4 text-ink-3">
        사용자 · 역할·권한 관리 (위험 변경은 확인 후 적용)
      </p>
      {error ? (
        <ErrorText className="mt-2">{error}</ErrorText>
      ) : !users || users.length === 0 ? (
        <EmptyState icon="users" title="사용자가 없어요" />
      ) : (
        <UsersTable users={users} />
      )}
    </div>
  );
}
