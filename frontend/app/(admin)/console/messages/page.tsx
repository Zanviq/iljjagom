import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
import { getAdminMessages } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { AdminMessage } from "@/lib/types";

function fmt(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString("ko-KR");
}

export default async function ConsoleMessagesPage() {
  const token = await getAccessToken();
  let messages: AdminMessage[] | null = null;
  let error: string | null = null;
  try {
    ({ messages } = await getAdminMessages(token, { limit: 100 }));
  } catch (e) {
    error = e instanceof Error ? e.message : "대화를 불러오지 못했어요.";
  }

  return (
    <div>
      <p className="ijg-eyebrow mb-4 text-ink-3">
        대화 기록 · 기획·편지·튜터 (열람도 감사 기록 / 미성년 데이터)
      </p>
      {error ? (
        <ErrorText className="mt-2">{error}</ErrorText>
      ) : !messages || messages.length === 0 ? (
        <EmptyState icon="messages-square" title="기록된 대화가 없어요" />
      ) : (
        <div className="overflow-x-auto rounded-[var(--radius-card)] border border-line">
          <table className="w-full min-w-[44rem] border-collapse bg-surface text-left">
            <thead>
              <tr className="border-b border-line bg-surface-2">
                {["종류", "역할", "내용", "시각"].map((h) => (
                  <th key={h} className="ijg-eyebrow p-3 text-ink-3" style={{ textAlign: "left" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {messages.map((m) => (
                <tr key={m.id} className="border-b border-line-soft last:border-0">
                  <td className="p-3 text-[length:var(--text-sm)] font-bold text-ink">
                    {m.kind}
                  </td>
                  <td className="p-3 text-[length:var(--text-sm)] text-ink-2">
                    {m.role}
                  </td>
                  <td className="max-w-md p-3 text-[length:var(--text-sm)] text-ink">
                    <span className="line-clamp-2">{m.content}</span>
                  </td>
                  <td
                    className="whitespace-nowrap p-3 text-ink-3"
                    style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
                  >
                    {fmt(m.createdAt)}
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
