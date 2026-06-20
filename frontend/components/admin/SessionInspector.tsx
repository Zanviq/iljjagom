"use client";

import { useEffect, useState } from "react";

import { SessionStatus } from "@/components/admin/SessionStatus";
import { Badge } from "@/components/ui/Badge";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { getAiSession } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { AiRole, AiSessionDetail, AiStep } from "@/lib/types";

const ROLE_LABEL: Record<AiRole, string> = {
  designer: "설계",
  writer: "집필",
  editor: "편집",
  chat: "대화",
  overseer: "총괄",
  letter: "편지",
};

/** ai_steps.args._prompt 에 적재된 프롬프트 스냅샷(백엔드 트레이스 확장). */
function stepPrompt(step: AiStep): { user?: string; chars?: number } | null {
  const args = step.args as { _prompt?: { user?: string; chars?: number } } | null;
  return args && typeof args === "object" && args._prompt ? args._prompt : null;
}

/**
 * 관리자 세션 인스펙터(04 기능개선 관리자/01). 세션 1건의 맥락·프롬프트·스텝·
 * 대화 전문·토큰을 한 패널에 표시. 프롬프트/대화는 미기록 시 graceful.
 */
export function SessionInspector({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<AiSessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const token = await getClientAccessToken();
        if (!active) return;
        setLoading(true);
        const s = await getAiSession(token, sessionId);
        if (active) setSession(s);
      } catch {
        if (active) setError("세션을 불러오지 못했어요.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [sessionId]);

  if (loading) {
    return <p className="p-5 text-[length:var(--text-sm)] text-ink-3">불러오는 중…</p>;
  }
  if (error || !session) {
    return (
      <p className="p-5 text-[length:var(--text-sm)] text-ink-3">
        {error ?? "세션을 찾을 수 없어요."}
      </p>
    );
  }

  const totalIn = session.steps.reduce((a, s) => a + (s.tokensIn || 0), 0);
  const totalOut = session.steps.reduce((a, s) => a + (s.tokensOut || 0), 0);
  const prompts = session.steps
    .map((s) => ({ idx: s.idx, skill: s.skill, prompt: stepPrompt(s) }))
    .filter((p) => p.prompt?.user);
  const ctx = session.context;

  return (
    <div className="flex flex-col gap-5 p-5">
      {/* 헤더 */}
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="primary">{ROLE_LABEL[session.role] ?? session.role}</Badge>
        <SessionStatus status={session.status} />
        <span
          className="text-ink-3"
          style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}
        >
          {session.model} · {session.id.slice(0, 8)}
        </span>
      </div>

      {/* 맥락 */}
      {(ctx || session.bookTitle || session.userEmail) && (
        <Section title="맥락">
          <dl className="flex flex-col gap-1 text-[length:var(--text-sm)]">
            <Row label="사용자" value={ctx?.userEmail ?? session.userEmail ?? "—"} />
            <Row label="책" value={ctx?.bookTitle ?? session.bookTitle ?? "—"} />
            <Row label="단계" value={ctx?.stage ?? session.stage ?? "—"} />
          </dl>
        </Section>
      )}

      {/* 들어간 프롬프트 */}
      <Section title="들어간 프롬프트">
        {prompts.length === 0 ? (
          <p className="text-[length:var(--text-sm)] text-ink-3">
            이 세션은 프롬프트 스냅샷 이전에 생성됐어요(미기록).
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {prompts.map((p) => (
              <details
                key={p.idx}
                className="rounded-[var(--radius-input)] border border-line bg-surface-2"
              >
                <summary className="cursor-pointer px-3 py-2 text-[length:var(--text-sm)] font-bold text-ink">
                  #{p.idx} {p.skill}
                  {p.prompt?.chars ? (
                    <span className="ml-1 font-normal text-ink-3">· {p.prompt.chars}자</span>
                  ) : null}
                </summary>
                <pre
                  className="overflow-x-auto whitespace-pre-wrap px-3 pb-3 text-ink-2"
                  style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}
                >
                  {p.prompt?.user}
                </pre>
              </details>
            ))}
          </div>
        )}
      </Section>

      {/* 스텝 */}
      <Section title={`스텝 (${session.steps.length})`}>
        {session.steps.length === 0 ? (
          <p className="text-[length:var(--text-sm)] text-ink-3">기록된 스텝이 없어요.</p>
        ) : (
          <ol className="flex flex-col gap-2">
            {session.steps.map((s) => (
              <li
                key={s.idx}
                className="rounded-[var(--radius-input)] border border-line bg-surface p-3"
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge tone="neutral">#{s.idx}</Badge>
                  <Badge tone="primary">{s.skill}</Badge>
                  <span
                    className="ml-auto text-ink-3"
                    style={{ fontFamily: "var(--font-mono)", fontSize: 10.5 }}
                  >
                    {s.tokensIn}/{s.tokensOut} · {s.ms}ms
                  </span>
                </div>
                {s.thought && (
                  <p className="mt-1.5 text-[length:var(--text-sm)] text-ink">{s.thought}</p>
                )}
                <JsonDetails label="결과(observation)" value={s.observation} />
              </li>
            ))}
          </ol>
        )}
      </Section>

      {/* 대화 전문 */}
      <Section title="대화 전문">
        {!session.transcript || session.transcript.length === 0 ? (
          <p className="text-[length:var(--text-sm)] text-ink-3">대화 기록이 없어요.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {session.transcript.map((m) => (
              <ChatBubble
                key={m.id}
                from={m.role === "user" ? "me" : "ai"}
                name={m.role === "user" ? undefined : ROLE_LABEL[session.role] ?? "AI"}
              >
                <span className="whitespace-pre-wrap">{m.content}</span>
              </ChatBubble>
            ))}
          </div>
        )}
      </Section>

      {/* 토큰 */}
      <Section title="토큰">
        <p
          className="text-ink"
          style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}
        >
          입력 {totalIn} · 출력 {totalOut}
        </p>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <p className="ijg-eyebrow mb-2 text-ink-3">{title}</p>
      {children}
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="w-14 flex-none text-ink-3">{label}</dt>
      <dd className="text-ink">{value}</dd>
    </div>
  );
}

function JsonDetails({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined) return null;
  return (
    <details className="mt-2 rounded-[var(--radius-input)] border border-line bg-surface-2">
      <summary className="cursor-pointer px-3 py-1.5 text-[length:var(--text-xs)] font-bold text-ink">
        {label}
      </summary>
      <pre
        className="overflow-x-auto px-3 pb-2 text-ink-2"
        style={{ fontFamily: "var(--font-mono)", fontSize: 10.5 }}
      >
        {JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}
