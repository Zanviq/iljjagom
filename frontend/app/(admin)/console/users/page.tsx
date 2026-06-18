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
      <h1 className="text-3xl font-extrabold">사용자 관리</h1>
      <p className="mt-1 text-muted">
        역할·권한을 관리해요. 위험 변경은 확인 후 적용돼요.
      </p>
      {error ? (
        <ErrorText className="mt-6">{error}</ErrorText>
      ) : !users || users.length === 0 ? (
        <EmptyState className="mt-6">사용자가 없어요.</EmptyState>
      ) : (
        <div className="mt-6">
          <UsersTable users={users} />
        </div>
      )}
    </div>
  );
}
