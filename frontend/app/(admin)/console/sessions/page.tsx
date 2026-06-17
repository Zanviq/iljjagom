import Link from "next/link";

import { SessionStatus } from "@/components/admin/SessionStatus";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
import { getAiSessions } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { AiRole, AiSession } from "@/lib/types";

const ROLE_LABEL: Record<AiRole, string> = {
  designer: "설계",
  writer: "집필",
  editor: "편집",
  chat: "대화",
};

function fmt(ts: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString("ko-KR");
}

export default async function ConsoleSessionsPage() {
  const token = await getAccessToken();

  let sessions: AiSession[] | null = null;
  let error: string | null = null;
  try {
    ({ sessions } = await getAiSessions(token, { limit: 100 }));
  } catch (e) {
    error = e instanceof Error ? e.message : "세션을 불러오지 못했어요.";
  }

  return (
    <div>
      <h1 className="text-3xl font-extrabold">AI 세션 / ReAct 트레이스</h1>
      <p className="mt-1 text-muted">
        AI 흐름의 역할·모델·상태·스텝을 봐요. 행을 누르면 트레이스 타임라인이 열려요.
      </p>

      {error ? (
        <ErrorText className="mt-6">{error}</ErrorText>
      ) : !sessions || sessions.length === 0 ? (
        <EmptyState className="mt-6">아직 기록된 AI 세션이 없어요.</EmptyState>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-card ring-1 ring-border">
          <table className="w-full min-w-[40rem] border-collapse bg-surface text-left">
            <thead>
              <tr className="border-b border-border text-sm text-muted">
                <th className="p-3 font-bold">역할</th>
                <th className="p-3 font-bold">모델</th>
                <th className="p-3 font-bold">상태</th>
                <th className="p-3 font-bold">요약</th>
                <th className="p-3 font-bold">시작</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr
                  key={s.id}
                  className="border-b border-border last:border-0 hover:bg-black/[0.02]"
                >
                  <td className="p-3 font-bold">
                    <Link
                      href={`/console/sessions/${s.id}`}
                      className="text-primary hover:underline"
                    >
                      {ROLE_LABEL[s.role] ?? s.role}
                    </Link>
                  </td>
                  <td className="p-3 text-sm text-muted">{s.model}</td>
                  <td className="p-3">
                    <SessionStatus status={s.status} />
                  </td>
                  <td className="p-3 text-sm">
                    {s.summary || <span className="text-muted">—</span>}
                  </td>
                  <td className="p-3 text-sm text-muted">{fmt(s.startedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
