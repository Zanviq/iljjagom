import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import {
  getAdminMessages,
  getMessagesByUser,
  getUserOverview,
} from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { AdminMessage, MessagesByUser, UserOverview } from "@/lib/types";

function fmt(ts: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString("ko-KR");
}

export default async function ConsoleMessagesPage({
  searchParams,
}: {
  searchParams: Promise<{ user?: string }>;
}) {
  const { user } = await searchParams;
  const token = await getAccessToken();

  return (
    <div>
      <p className="ijg-eyebrow mb-4 text-ink-3">
        대화 기록 · 사용자별 (열람도 감사 기록 / 미성년 데이터)
      </p>
      {user ? (
        <UserDrilldown token={token} userId={user} />
      ) : (
        <UserList token={token} />
      )}
    </div>
  );
}

async function UserList({ token }: { token: string | null }) {
  let grouped: MessagesByUser | null = null;
  try {
    grouped = await getMessagesByUser(token);
  } catch {
    grouped = null;
  }

  // groupBy=user 미구현이면 평면 대화 목록으로 폴백.
  if (!grouped) {
    let messages: AdminMessage[] = [];
    try {
      ({ messages } = await getAdminMessages(token, { limit: 100 }));
    } catch {
      messages = [];
    }
    if (messages.length === 0) {
      return <EmptyState icon="messages-square" title="기록된 대화가 없어요" />;
    }
    return <FlatMessages messages={messages} />;
  }

  if (grouped.users.length === 0) {
    return <EmptyState icon="messages-square" title="기록된 대화가 없어요" />;
  }

  return (
    <div className="overflow-x-auto rounded-[var(--radius-card)] border border-line">
      <table className="w-full min-w-[40rem] border-collapse bg-surface text-left">
        <thead>
          <tr className="border-b border-line bg-surface-2">
            {["사용자", "역할", "책", "대화", "최근"].map((h) => (
              <th key={h} className="ijg-eyebrow p-3 text-ink-3" style={{ textAlign: "left" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grouped.users.map((u) => (
            <tr key={u.userId} className="border-b border-line-soft last:border-0 hover:bg-surface-inset">
              <td className="p-3 font-bold">
                <Link href={`/console/messages?user=${u.userId}`} className="text-primary-text hover:underline">
                  {u.email}
                </Link>
              </td>
              <td className="p-3 text-[length:var(--text-sm)] text-ink-2">{u.role}</td>
              <td className="p-3" style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}>
                {u.bookCount}
              </td>
              <td className="p-3" style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}>
                {u.messageCount}
              </td>
              <td className="p-3 text-ink-3" style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
                {fmt(u.lastAt)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

async function UserDrilldown({
  token,
  userId,
}: {
  token: string | null;
  userId: string;
}) {
  let ov: UserOverview | null = null;
  let error: string | null = null;
  try {
    ov = await getUserOverview(token, userId);
  } catch {
    error = "이 사용자 기록을 준비하고 있어요.";
  }

  const back = (
    <Link
      href="/console/messages"
      className="inline-flex items-center gap-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
    >
      <Icon name="arrow-left" size={16} />
      사용자 목록
    </Link>
  );

  if (error || !ov) {
    return (
      <div>
        {back}
        <EmptyState icon="user" title="사용자 기록을 볼 수 없어요" className="mt-4">
          {error}
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {back}
      <div>
        <h1 className="text-[length:var(--text-lg)] font-extrabold text-ink">{ov.user.email}</h1>
        <p className="text-[length:var(--text-sm)] text-ink-3">{ov.user.role}</p>
      </div>

      <section>
        <p className="ijg-eyebrow mb-2 text-ink-3">책 ({ov.books.length})</p>
        {ov.books.length === 0 ? (
          <p className="text-[length:var(--text-sm)] text-ink-3">만든 책이 없어요.</p>
        ) : (
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(240px,1fr))]">
            {ov.books.map((b) => (
              <Card key={b.id} padding="md">
                <p className="font-bold text-ink">{b.title || "제목 없음"}</p>
                <p className="mt-1 text-ink-3" style={{ fontFamily: "var(--font-mono)", fontSize: 11.5 }}>
                  세션 {b.sessionCount} · 대화 {b.messageCount}
                </p>
                <Badge tone="neutral" className="mt-2">
                  {b.status}
                </Badge>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <p className="ijg-eyebrow mb-2 text-ink-3">세션 ({ov.sessions.length})</p>
        {ov.sessions.length === 0 ? (
          <p className="text-[length:var(--text-sm)] text-ink-3">기록된 세션이 없어요.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {ov.sessions.map((s) => (
              <Link
                key={s.id}
                href={`/console/sessions?sid=${s.id}`}
                className="flex items-center justify-between gap-3 rounded-[var(--radius-input)] border border-line bg-surface px-3.5 py-2.5 hover:bg-surface-inset"
              >
                <span className="text-[length:var(--text-sm)] font-bold text-ink">
                  {s.bookTitle || s.stage || s.role}
                </span>
                <span className="text-ink-3" style={{ fontFamily: "var(--font-mono)", fontSize: 11.5 }}>
                  {s.role} · {fmt(s.startedAt)}
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <p className="ijg-eyebrow mb-2 text-ink-3">최근 대화</p>
        {ov.recentMessages.length === 0 ? (
          <p className="text-[length:var(--text-sm)] text-ink-3">대화가 없어요.</p>
        ) : (
          <FlatMessages messages={ov.recentMessages} />
        )}
      </section>
    </div>
  );
}

function FlatMessages({ messages }: { messages: AdminMessage[] }) {
  return (
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
              <td className="p-3 text-[length:var(--text-sm)] font-bold text-ink">{m.kind}</td>
              <td className="p-3 text-[length:var(--text-sm)] text-ink-2">{m.role}</td>
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
  );
}
