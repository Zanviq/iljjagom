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
      <p className="ijg-eyebrow mb-4 text-ink-3">
        실시간 AI 세션 · 역할·모델·상태·스텝 (행을 누르면 트레이스)
      </p>

      {error ? (
        <ErrorText className="mt-2">{error}</ErrorText>
      ) : !sessions || sessions.length === 0 ? (
        <EmptyState icon="activity" title="아직 기록된 AI 세션이 없어요" />
      ) : (
        <div className="overflow-x-auto rounded-[var(--radius-card)] border border-line">
          <table className="w-full min-w-[40rem] border-collapse bg-surface text-left">
            <thead>
              <tr className="border-b border-line bg-surface-2">
                {["역할", "모델", "사용자", "상태", "요약", "시작"].map((h) => (
                  <th key={h} className="ijg-eyebrow p-3 text-ink-3" style={{ textAlign: "left" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr
                  key={s.id}
                  className="border-b border-line-soft last:border-0 hover:bg-surface-inset"
                >
                  <td className="p-3 font-bold">
                    <Link
                      href={`/console/sessions/${s.id}`}
                      className="text-primary-text hover:underline"
                    >
                      {ROLE_LABEL[s.role] ?? s.role}
                    </Link>
                  </td>
                  <td
                    className="p-3 text-ink-2"
                    style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}
                  >
                    {s.model}
                  </td>
                  <td className="p-3 text-[length:var(--text-sm)] text-ink-2">
                    {s.userEmail || "—"}
                  </td>
                  <td className="p-3">
                    <SessionStatus status={s.status} />
                  </td>
                  <td className="p-3 text-[length:var(--text-sm)] text-ink">
                    {s.summary || <span className="text-ink-3">—</span>}
                  </td>
                  <td
                    className="p-3 text-ink-3"
                    style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
                  >
                    {fmt(s.startedAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
