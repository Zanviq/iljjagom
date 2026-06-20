"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ChatBubble } from "@/components/ui/ChatBubble";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import {
  ApiError,
  getBible,
  getBookLetters,
  getChaptersContent,
  getLearningResults,
  getPlanMessages,
} from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type {
  ChapterContent,
  LearningResult,
  Letter,
  PlanMessage,
} from "@/lib/types";

type TabKey = "body" | "plan" | "bible" | "learning" | "letter";

const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: "body", label: "본문", icon: "book-open" },
  { key: "plan", label: "기획 대화", icon: "messages-square" },
  { key: "bible", label: "설계", icon: "scroll-text" },
  { key: "learning", label: "학습 결과", icon: "graduation-cap" },
  { key: "letter", label: "편지", icon: "mail" },
];

/** 교사용 학생 작업 열람(04 기능개선 교사/03). 읽기 전용 탭. 미구현 시 graceful. */
export function StudentWorkViewer({ bookId }: { bookId: string }) {
  const [tab, setTab] = useState<TabKey>("body");
  const [chapters, setChapters] = useState<ChapterContent[] | null>(null);
  const [plan, setPlan] = useState<PlanMessage[] | null>(null);
  const [bible, setBible] = useState<Record<string, unknown> | null>(null);
  const [learning, setLearning] = useState<LearningResult[] | null>(null);
  const [letters, setLetters] = useState<Letter[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const loaded =
      (tab === "body" && chapters) ||
      (tab === "plan" && plan) ||
      (tab === "bible" && bible) ||
      (tab === "learning" && learning) ||
      (tab === "letter" && letters);
    if (loaded) return;
    (async () => {
      try {
        const token = await getClientAccessToken();
        if (!active) return;
        setLoading(true);
        setError(null);
        if (tab === "body") {
          const { chapters: cs } = await getChaptersContent(token, bookId);
          if (active) setChapters(cs);
        } else if (tab === "plan") {
          const { messages } = await getPlanMessages(token, bookId);
          if (active) setPlan(messages);
        } else if (tab === "bible") {
          const { bible: b } = await getBible(token, bookId);
          if (active) setBible(b);
        } else if (tab === "learning") {
          const { results } = await getLearningResults(token, bookId);
          if (active) setLearning(results);
        } else {
          const { letters: ls } = await getBookLetters(token, bookId);
          if (active) setLetters(ls);
        }
      } catch (e) {
        if (active)
          setError(
            e instanceof ApiError && (e.status === 404 || e.status === 0)
              ? "이 자료를 준비하고 있어요. 조금만 기다려 주세요."
              : "자료를 불러오지 못했어요.",
          );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [tab, bookId, chapters, plan, bible, learning, letters]);

  return (
    <div>
      <div className="mb-5 flex flex-wrap gap-1.5">
        {TABS.map((t) => {
          const sel = tab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              aria-pressed={sel}
              className="inline-flex items-center gap-1.5 rounded-[var(--radius-control)] px-3.5 py-2 text-[length:var(--text-sm)] font-bold"
              style={{
                cursor: "pointer",
                background: sel ? "var(--primary)" : "var(--surface-2)",
                color: sel ? "var(--on-primary)" : "var(--text-2)",
                border: sel
                  ? "var(--border) solid transparent"
                  : "var(--border) solid var(--line)",
              }}
            >
              <Icon name={t.icon} size={16} />
              {t.label}
            </button>
          );
        })}
      </div>

      {loading ? (
        <p className="text-[length:var(--text-sm)] text-ink-3">불러오는 중이에요…</p>
      ) : error ? (
        <EmptyState icon="file-question" title="자료를 볼 수 없어요">
          {error}
        </EmptyState>
      ) : tab === "body" ? (
        <BodyView chapters={chapters ?? []} />
      ) : tab === "plan" ? (
        <PlanView messages={plan ?? []} />
      ) : tab === "bible" ? (
        <BibleView bible={bible ?? {}} />
      ) : tab === "learning" ? (
        <LearningView results={learning ?? []} />
      ) : (
        <LetterView letters={letters ?? []} />
      )}
    </div>
  );
}

function LetterView({ letters }: { letters: Letter[] }) {
  if (letters.length === 0) {
    return (
      <EmptyState icon="mail" title="주고받은 편지가 없어요">
        학생이 이야기 속 인물에게 편지를 쓰면 여기에 보여요.
      </EmptyState>
    );
  }
  const STATUS: Record<string, { label: string; tone: "neutral" | "primary" | "success" | "danger" }> = {
    pending: { label: "확인 전", tone: "neutral" },
    answered: { label: "답장 받음", tone: "success" },
    held: { label: "확인 보류", tone: "danger" },
    approved: { label: "승인됨", tone: "success" },
    rejected: { label: "반려됨", tone: "danger" },
  };
  return (
    <div className="flex flex-col gap-4">
      {letters.map((l) => {
        const st = STATUS[l.status] ?? { label: l.status, tone: "neutral" as const };
        return (
          <Card key={l.id} padding="lg">
            <div className="mb-2.5 flex items-center justify-between gap-2">
              <Badge tone="accent">{l.recipient}에게</Badge>
              <Badge tone={st.tone} dot>
                {st.label}
              </Badge>
            </div>
            <p
              className="whitespace-pre-wrap"
              style={{ fontSize: "var(--text-md)", lineHeight: "var(--leading-normal)", color: "var(--text-1)" }}
            >
              {l.body}
            </p>
            {l.reply && (
              <div className="mt-3 rounded-[var(--radius-input)] bg-surface-inset p-3">
                <p className="ijg-eyebrow mb-1.5" style={{ color: "var(--accent-text)" }}>
                  {l.recipient}의 답장
                </p>
                <p
                  className="whitespace-pre-wrap text-[length:var(--text-sm)]"
                  style={{ color: "var(--text-2)" }}
                >
                  {l.reply}
                </p>
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

function BodyView({ chapters }: { chapters: ChapterContent[] }) {
  if (chapters.length === 0) {
    return (
      <EmptyState icon="book-open" title="아직 쓴 본문이 없어요">
        학생이 이야기를 쓰면 여기에 보여요.
      </EmptyState>
    );
  }
  return (
    <div className="flex flex-col gap-6">
      {chapters.map((c) => (
        <Card key={c.idx} padding="lg">
          <div className="mb-3 flex items-center gap-2">
            <Badge tone="primary" dot>
              {c.idx}장
            </Badge>
            <Badge tone="neutral">{c.mode === "free" ? "자유집필" : "유도집필"}</Badge>
            <span
              className="text-ink-3"
              style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
            >
              {c.charCount}자
            </span>
          </div>
          <p
            className="whitespace-pre-wrap"
            style={{ fontSize: "var(--text-md)", lineHeight: "var(--leading-normal)", color: "var(--text-1)" }}
          >
            {c.body || "(아직 본문이 없어요)"}
          </p>
        </Card>
      ))}
    </div>
  );
}

function PlanView({ messages }: { messages: PlanMessage[] }) {
  if (messages.length === 0) {
    return (
      <EmptyState icon="messages-square" title="기획 대화가 없어요">
        학생이 곰 작가와 나눈 대화가 여기에 보여요.
      </EmptyState>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {messages.map((m, i) => (
        <ChatBubble
          key={i}
          from={m.role === "student" ? "me" : "ai"}
          name={m.role === "interviewer" ? "곰 작가" : undefined}
        >
          <span className="whitespace-pre-wrap">{m.content}</span>
        </ChatBubble>
      ))}
    </div>
  );
}

function BibleView({ bible }: { bible: Record<string, unknown> }) {
  const entries = Object.entries(bible);
  if (entries.length === 0) {
    return (
      <EmptyState icon="scroll-text" title="설계 정보가 없어요">
        이야기를 설계하면 인물·세계관이 여기에 보여요.
      </EmptyState>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {entries.map(([key, value]) => (
        <Card key={key} padding="lg">
          <p className="ijg-eyebrow mb-2" style={{ color: "var(--primary-text)" }}>
            {key}
          </p>
          <BibleValue value={value} />
        </Card>
      ))}
    </div>
  );
}

function BibleValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="text-ink-faint">—</span>;
  }
  if (typeof value === "string" || typeof value === "number") {
    return (
      <p className="whitespace-pre-wrap text-[length:var(--text-sm)] text-ink-1">
        {String(value)}
      </p>
    );
  }
  return (
    <pre
      className="overflow-x-auto rounded-[var(--radius-input)] bg-surface-inset p-3 text-[length:var(--text-xs)] text-ink-2"
      style={{ fontFamily: "var(--font-mono)" }}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function LearningView({ results }: { results: LearningResult[] }) {
  if (results.length === 0) {
    return (
      <EmptyState icon="graduation-cap" title="학습 결과가 없어요">
        학생이 학습 활동을 하면 여기에 쌓여요.
      </EmptyState>
    );
  }
  const LABEL: Record<string, string> = {
    quiz: "퀴즈",
    essay: "독후감",
    emotion: "감정 곡선",
    letter: "편지",
  };
  return (
    <div className="flex flex-col gap-3">
      {results.map((r) => (
        <Card key={r.id} padding="md">
          <div className="mb-2 flex items-center justify-between">
            <Badge tone="accent">{LABEL[r.type] ?? r.type}</Badge>
            <span
              className="text-ink-3"
              style={{ fontFamily: "var(--font-mono)", fontSize: 11.5 }}
            >
              {new Date(r.createdAt).toLocaleString("ko-KR")}
            </span>
          </div>
          <pre
            className="overflow-x-auto rounded-[var(--radius-input)] bg-surface-inset p-3 text-[length:var(--text-xs)] text-ink-2"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {JSON.stringify(r.data, null, 2)}
          </pre>
        </Card>
      ))}
    </div>
  );
}
