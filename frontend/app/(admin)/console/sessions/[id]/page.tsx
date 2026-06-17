import Link from "next/link";

import { SessionStatus } from "@/components/admin/SessionStatus";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
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
      <Link href="/console/sessions" className="text-sm font-bold text-muted">
        ← AI 세션 목록
      </Link>

      {error ? (
        <ErrorText className="mt-4">{error}</ErrorText>
      ) : !session ? (
        <EmptyState className="mt-4">세션을 찾을 수 없어요.</EmptyState>
      ) : (
        <>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-extrabold">
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
            <p className="mt-4 rounded-card bg-surface p-4 ring-1 ring-border">
              {session.summary}
            </p>
          )}
          {session.error && (
            <ErrorText className="mt-4">{session.error}</ErrorText>
          )}

          <h2 className="mb-3 mt-8 text-lg font-bold">스텝 타임라인</h2>
          {session.steps.length === 0 ? (
            <EmptyState>기록된 스텝이 없어요.</EmptyState>
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
    <div className="rounded-card bg-surface p-3 ring-1 ring-border">
      <dt className="text-xs font-bold text-muted">{label}</dt>
      <dd className="mt-1 font-bold">{value}</dd>
    </div>
  );
}

function StepCard({ step }: { step: AiStep }) {
  return (
    <li className="rounded-card bg-surface p-4 ring-1 ring-border">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-black/5 px-2 py-0.5 text-xs font-bold text-muted">
          #{step.idx}
        </span>
        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-sm font-bold text-primary">
          {step.skill}
        </span>
        <span className="ml-auto text-xs text-muted">
          토큰 {step.tokensIn}/{step.tokensOut} · {step.ms}ms
        </span>
      </div>

      {step.thought && (
        <p className="mt-2 text-sm">
          <span className="font-bold text-muted">생각: </span>
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
    <details className="rounded-xl bg-background ring-1 ring-border">
      <summary className="cursor-pointer px-3 py-2 text-sm font-bold">
        {label}
      </summary>
      <pre className="overflow-x-auto px-3 pb-3 text-xs text-muted">
        {JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}
