import Link from "next/link";

import { SessionStatus } from "@/components/admin/SessionStatus";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
import { Icon } from "@/components/ui/Icon";
import { getAiSession } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { AiRole, AiSessionDetail, AiStep } from "@/lib/types";

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

/**
 * 세션 상세 = ReAct 흐름 시각화(06 §3.3): 스텝 타임라인(thought/skill/args/observation/tokens/ms).
 * args/observation은 접이식(<details>)으로 펼쳐 본다.
 */
export default async function ConsoleSessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const token = await getAccessToken();

  let session: AiSessionDetail | null = null;
  let error: string | null = null;
  try {
    session = await getAiSession(token, id);
  } catch (e) {
    error = e instanceof Error ? e.message : "세션을 불러오지 못했어요.";
  }

  const totalIn = session?.steps.reduce((a, s) => a + (s.tokensIn || 0), 0) ?? 0;
  const totalOut =
    session?.steps.reduce((a, s) => a + (s.tokensOut || 0), 0) ?? 0;

  return (
    <div>
      <Link
        href="/console/sessions"
        className="inline-flex items-center gap-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
      >
        <Icon name="arrow-left" size={16} />
        AI 세션 목록
      </Link>

      {error ? (
        <ErrorText className="mt-4">{error}</ErrorText>
      ) : !session ? (
        <EmptyState icon="activity" title="세션을 찾을 수 없어요" className="mt-4" />
      ) : (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h1 className="text-[length:var(--text-lg)] font-extrabold text-ink">
              {ROLE_LABEL[session.role] ?? session.role} 세션
            </h1>
            <SessionStatus status={session.status} />
          </div>

          <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Meta label="모델" value={session.model} />
            <Meta label="스텝" value={`${session.steps.length}개`} />
            <Meta label="토큰(입/출)" value={`${totalIn} / ${totalOut}`} />
            <Meta label="시작" value={fmt(session.startedAt)} />
          </dl>

          {session.summary && (
            <Card padding="md" className="mt-4">
              <p className="text-ink">{session.summary}</p>
            </Card>
          )}
          {session.error && <ErrorText className="mt-4">{session.error}</ErrorText>}

          <h2 className="mb-3 mt-8 text-[length:var(--text-md)] font-extrabold text-ink">
            스텝 타임라인
          </h2>
          {session.steps.length === 0 ? (
            <EmptyState icon="activity" title="기록된 스텝이 없어요" />
          ) : (
            <ol className="space-y-3">
              {session.steps.map((step) => (
                <StepCard key={step.idx} step={step} />
              ))}
            </ol>
          )}
        </>
      )}
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-line bg-surface p-3">
      <dt className="ijg-eyebrow text-ink-3">{label}</dt>
      <dd className="mt-1 font-bold text-ink">{value}</dd>
    </div>
  );
}

function StepCard({ step }: { step: AiStep }) {
  return (
    <li className="rounded-[var(--radius-card)] border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="neutral">#{step.idx}</Badge>
        <Badge tone="primary">{step.skill}</Badge>
        <span
          className="ml-auto text-ink-3"
          style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}
        >
          토큰 {step.tokensIn}/{step.tokensOut} · {step.ms}ms
        </span>
      </div>

      {step.thought && (
        <p className="mt-2 text-[length:var(--text-sm)] text-ink">
          <span className="font-bold text-ink-3">생각: </span>
          {step.thought}
        </p>
      )}

      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <JsonDetails label="입력(args)" value={step.args} />
        <JsonDetails label="결과(observation)" value={step.observation} />
      </div>
    </li>
  );
}

function JsonDetails({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined) return null;
  return (
    <details className="rounded-[var(--radius-input)] border border-line bg-surface-2">
      <summary className="cursor-pointer px-3 py-2 text-[length:var(--text-sm)] font-bold text-ink">
        {label}
      </summary>
      <pre
        className="overflow-x-auto px-3 pb-3 text-ink-2"
        style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}
      >
        {JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}
