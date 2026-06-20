"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { ApiError, getBookTimeline } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { AiRole, BookStatus, BookTimeline as BookTimelineData } from "@/lib/types";

const ROLE_LABEL: Record<AiRole, string> = {
  designer: "설계",
  writer: "집필",
  editor: "검수",
  chat: "대화",
  overseer: "총괄",
  letter: "편지",
};

const STATUS_LABEL: Record<BookStatus, string> = {
  planning: "기획 중",
  writing: "집필 중",
  done: "완독",
};

function fmt(ts?: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString("ko-KR");
}

/**
 * 책 단계별 통합 타임라인(04 기능개선 관리자/01). 한 책의 발제→설계→집필→학습을
 * 한 화면에서 본다. 미구현(404)이면 graceful 안내.
 */
export function BookTimeline({ bookId }: { bookId: string }) {
  const [data, setData] = useState<BookTimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const token = await getClientAccessToken();
        const res = await getBookTimeline(token, bookId);
        if (active) setData(res);
      } catch (e) {
        if (!active) return;
        setError(
          e instanceof ApiError && (e.status === 404 || e.status === 0)
            ? "이 책의 타임라인을 준비하고 있어요."
            : "타임라인을 불러오지 못했어요.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [bookId]);

  if (loading) {
    return <p className="text-[length:var(--text-sm)] text-ink-3">불러오는 중이에요…</p>;
  }
  if (error || !data) {
    return (
      <EmptyState icon="file-question" title="타임라인을 볼 수 없어요">
        {error}
      </EmptyState>
    );
  }

  const { book, prompt, chapters, sessions, planMessages, messages, learning } = data;

  return (
    <div className="flex flex-col gap-7">
      <div>
        <div className="flex items-center gap-2.5">
          <h1 className="text-[length:var(--text-lg)] font-extrabold text-ink">
            {book.title || "제목 없음"}
          </h1>
          <Badge tone="neutral">{STATUS_LABEL[book.status] ?? book.status}</Badge>
        </div>
        <p className="mt-1 text-[length:var(--text-sm)] text-ink-3">
          {book.studentEmail ? `${book.studentEmail} · ` : ""}
          {fmt(book.createdAt)}
        </p>
      </div>

      {prompt && (
        <Section icon="pencil" title="발제">
          <Card padding="md">
            <p className="font-bold text-ink">{prompt.topic}</p>
            {prompt.learningObjectives.length > 0 && (
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {prompt.learningObjectives.map((o, i) => (
                  <li
                    key={i}
                    className="rounded-full bg-accent-tint px-2.5 py-0.5 text-[length:var(--text-sm)] text-accent-text"
                  >
                    {o}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </Section>
      )}

      <Section icon="layers" title={`챕터 (${chapters.length})`}>
        {chapters.length === 0 ? (
          <Empty>아직 집필된 챕터가 없어요.</Empty>
        ) : (
          <div className="flex flex-wrap gap-2">
            {chapters.map((c) => (
              <div
                key={c.idx}
                className="flex items-center gap-2 rounded-[var(--radius-input)] border border-line bg-surface px-3 py-2"
              >
                <Badge tone="primary" dot>
                  {c.idx}장
                </Badge>
                <span
                  className="text-ink-3"
                  style={{ fontFamily: "var(--font-mono)", fontSize: 11.5 }}
                >
                  {c.charCount}자 · {c.reviewStatus}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section icon="bot" title={`AI 세션 (${sessions.length})`}>
        {sessions.length === 0 ? (
          <Empty>기록된 세션이 없어요.</Empty>
        ) : (
          <div className="flex flex-col gap-2">
            {sessions.map((s) => (
              <Link
                key={s.id}
                href={`/console/sessions?sid=${s.id}`}
                className="flex items-center justify-between gap-3 rounded-[var(--radius-input)] border border-line bg-surface px-3.5 py-2.5 hover:bg-surface-inset"
              >
                <span className="flex items-center gap-2 text-[length:var(--text-sm)] font-bold text-ink">
                  <Badge tone="neutral">{ROLE_LABEL[s.role] ?? s.role}</Badge>
                  {s.stage || s.summary || s.model}
                </span>
                <span className="text-ink-3" style={{ fontFamily: "var(--font-mono)", fontSize: 11.5 }}>
                  {fmt(s.startedAt)}
                </span>
              </Link>
            ))}
          </div>
        )}
      </Section>

      <Section icon="messages-square" title={`기획 대화 (${planMessages.length})`}>
        {planMessages.length === 0 ? (
          <Empty>기획 대화가 없어요.</Empty>
        ) : (
          <div className="flex flex-col gap-3">
            {planMessages.map((m, i) => (
              <ChatBubble
                key={i}
                from={m.role === "student" ? "me" : "ai"}
                name={m.role === "interviewer" ? "곰 작가" : undefined}
              >
                <span className="whitespace-pre-wrap">{m.content}</span>
              </ChatBubble>
            ))}
          </div>
        )}
      </Section>

      <Section icon="graduation-cap" title={`학습 결과 (${learning.length})`}>
        {learning.length === 0 ? (
          <Empty>학습 결과가 없어요.</Empty>
        ) : (
          <div className="flex flex-col gap-2">
            {learning.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between gap-3 rounded-[var(--radius-input)] border border-line bg-surface px-3.5 py-2.5"
              >
                <Badge tone="accent">{r.type}</Badge>
                <span className="text-ink-3" style={{ fontFamily: "var(--font-mono)", fontSize: 11.5 }}>
                  {fmt(r.createdAt)}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      {messages.length > 0 && (
        <Section icon="list" title={`전체 대화 (${messages.length})`}>
          <p className="text-[length:var(--text-sm)] text-ink-3">
            세션별 전문은 위 AI 세션에서 열어 볼 수 있어요.
          </p>
        </Section>
      )}
    </div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-3 flex items-center gap-2">
        <Icon name={icon} size={17} style={{ color: "var(--text-3)" }} />
        <h2 className="text-[length:var(--text-md)] font-extrabold text-ink">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-[length:var(--text-sm)] text-ink-3">{children}</p>;
}
