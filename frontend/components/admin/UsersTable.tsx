"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmModal } from "@/components/admin/ConfirmModal";
import { ApiError, deactivateAdminUser, patchAdminUser } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { AdminUser, Role } from "@/lib/types";

const ROLES: Role[] = ["student", "teacher", "admin"];
const ROLE_LABEL: Record<Role, string> = {
  student: "학생",
  teacher: "교사",
  admin: "관리자",
};

type Action =
  | { kind: "role"; user: AdminUser; role: Role }
  | { kind: "deactivate"; user: AdminUser };

export function UsersTable({ users }: { users: AdminUser[] }) {
  const router = useRouter();
  const [action, setAction] = useState<Action | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    if (!action) return;
    setPending(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      if (action.kind === "role") {
        await patchAdminUser(token, action.user.id, { role: action.role });
      } else {
        await deactivateAdminUser(token, action.user.id);
      }
      setAction(null);
      router.refresh();
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "변경하지 못했어요.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <div className="overflow-x-auto rounded-card ring-1 ring-border">
        <table className="w-full min-w-[44rem] border-collapse bg-surface text-left">
          <thead>
            <tr className="border-b border-border text-sm text-muted">
              <th className="p-3 font-bold">이메일</th>
              <th className="p-3 font-bold">역할</th>
              <th className="p-3 font-bold">학급</th>
              <th className="p-3 font-bold">상태</th>
              <th className="p-3 font-bold">작업</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-border last:border-0">
                <td className="p-3 text-sm font-medium">{u.email}</td>
                <td className="p-3">
                  <select
                    value={u.role}
                    disabled={u.status === "deactivated"}
                    onChange={(e) =>
                      setAction({
                        kind: "role",
                        user: u,
                        role: e.target.value as Role,
                      })
                    }
                    className="rounded-lg border-2 border-border bg-background px-2 py-1 text-sm font-bold"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {ROLE_LABEL[r]}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="p-3 text-sm text-muted">
                  {u.className || "—"}
                </td>
                <td className="p-3 text-sm">
                  {u.status === "active" ? (
                    <span className="font-bold text-success-strong">활성</span>
                  ) : (
                    <span className="font-bold text-muted">비활성</span>
                  )}
                </td>
                <td className="p-3">
                  {u.status === "active" && (
                    <button
                      onClick={() => setAction({ kind: "deactivate", user: u })}
                      className="rounded-lg px-3 py-1 text-sm font-bold text-danger hover:bg-danger/10"
                    >
                      비활성
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {action && (
        <ConfirmModal
          title={action.kind === "role" ? "역할 변경" : "사용자 비활성"}
          body={
            <>
              <p>
                <strong>{action.user.email}</strong>
                {action.kind === "role"
                  ? ` 의 역할을 ${ROLE_LABEL[action.role]}(으)로 바꿀까요?`
                  : " 을(를) 비활성화할까요?"}
              </p>
              {error && <p className="mt-2 font-bold text-danger">{error}</p>}
            </>
          }
          confirmLabel={action.kind === "role" ? "변경" : "비활성"}
          danger={action.kind === "deactivate"}
          pending={pending}
          onConfirm={() => void confirm()}
          onCancel={() => {
            setAction(null);
            setError(null);
          }}
        />
      )}
    </>
  );
}
