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
      <h1 className="text-3xl font-extrabold">대화 기록</h1>
      <p className="mt-1 text-muted">
        기획·편지·튜터 대화예요. 열람도 감사 기록됩니다(미성년 데이터).
      </p>
      {error ? (
        <ErrorText className="mt-6">{error}</ErrorText>
      ) : !messages || messages.length === 0 ? (
        <EmptyState className="mt-6">기록된 대화가 없어요.</EmptyState>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-card ring-1 ring-border">
          <table className="w-full min-w-[44rem] border-collapse bg-surface text-left">
            <thead>
              <tr className="border-b border-border text-sm text-muted">
                <th className="p-3 font-bold">종류</th>
                <th className="p-3 font-bold">역할</th>
                <th className="p-3 font-bold">내용</th>
                <th className="p-3 font-bold">시각</th>
              </tr>
            </thead>
            <tbody>
              {messages.map((m) => (
                <tr key={m.id} className="border-b border-border last:border-0">
                  <td className="p-3 text-sm font-bold">{m.kind}</td>
                  <td className="p-3 text-sm text-muted">{m.role}</td>
                  <td className="max-w-md p-3 text-sm">
                    <span className="line-clamp-2">{m.content}</span>
                  </td>
                  <td className="whitespace-nowrap p-3 text-sm text-muted">
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
