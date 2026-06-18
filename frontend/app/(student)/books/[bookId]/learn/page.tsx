import Link from "next/link";
import { notFound } from "next/navigation";

import { EssayForm } from "@/components/learning/EssayForm";
import { LearningOpenTracker } from "@/components/learning/LearningOpenTracker";
import { LetterForm } from "@/components/learning/LetterForm";
import { Quiz } from "@/components/learning/Quiz";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { ApiError, getBook, getLearning } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { EmotionPoint, Word } from "@/lib/types";

export default async function LearnPage({
  params,
}: {
  params: Promise<{ bookId: string }>;
}) {
  const { bookId } = await params;
  const token = await getAccessToken();

  const [book, learning] = await Promise.all([
    getBook(token, bookId).catch((e) => {
      if (e instanceof ApiError && e.status === 404) notFound();
      throw e;
    }),
    getLearning(token, bookId).catch((e) => {
      if (e instanceof ApiError && e.status === 404) notFound();
      throw e;
    }),
  ]);

  const { vocab, quiz, essayBlanks, emotion } = learning;
  const isEmpty =
    vocab.length === 0 &&
    quiz.length === 0 &&
    essayBlanks.length === 0 &&
    emotion.length === 0;

  return (
    <div className="mx-auto w-full max-w-[740px] px-6 pb-20 pt-6">
      <LearningOpenTracker bookId={bookId} />
      <Link
        href={`/books/${bookId}/read`}
        className="inline-flex items-center gap-1.5 py-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
      >
        <Icon name="arrow-left" size={16} />
        이야기로 돌아가기
      </Link>
      <h1
        className="mb-1 mt-2"
        style={{
          fontFamily: "var(--font-serif)",
          fontWeight: 600,
          fontSize: 36,
          letterSpacing: "-.02em",
          color: "var(--text-1)",
        }}
      >
        학습 활동{book.title ? ` · ${book.title}` : ""}
      </h1>
      <p className="mb-7 text-[length:var(--text-md)] text-ink-2">
        이야기로 낱말도 배우고 생각도 나눠 봐요.
      </p>

      {isEmpty ? (
        <EmptyState icon="graduation-cap" title="아직 학습 활동이 없어요">
          아직 학습 활동이 준비되지 않았어요. 이야기를 더 읽고 와요!
        </EmptyState>
      ) : (
        <div className="flex flex-col gap-9">
          {vocab.length > 0 && (
            <Block icon="book-a" title="낱말 카드">
              <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(220px,1fr))]">
                {vocab.map((w, i) => (
                  <VocabCard key={i} word={w} />
                ))}
              </div>
            </Block>
          )}

          {quiz.length > 0 && (
            <Block icon="circle-help" title="퀴즈">
              <Quiz items={quiz} bookId={bookId} />
            </Block>
          )}

          {essayBlanks.length > 0 && (
            <Block icon="notebook-pen" title="독후감 채우기">
              <EssayForm bookId={bookId} blanks={essayBlanks} />
            </Block>
          )}

          {emotion.length > 0 && (
            <Block icon="pen-line" title="감정 곡선">
              <EmotionCurve points={emotion} />
            </Block>
          )}

          <Block icon="mail" title="인물에게 편지 쓰기">
            <LetterForm bookId={bookId} />
          </Block>
        </div>
      )}
    </div>
  );
}

function Block({
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
      <div className="mb-3.5 flex items-center gap-2.5">
        <span
          className="flex h-[34px] w-[34px] items-center justify-center rounded-[10px]"
          style={{ background: "var(--accent-tint)", color: "var(--accent-text)" }}
          aria-hidden
        >
          <Icon name={icon} size={18} />
        </span>
        <h2 className="text-[length:var(--text-lg)] font-extrabold text-ink">
          {title}
        </h2>
      </div>
      {children}
    </section>
  );
}

function VocabCard({ word }: { word: Word }) {
  return (
    <Card padding="md">
      <p style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 20, color: "var(--text-1)" }}>
        {word.term}
        {word.reading && word.reading !== word.term && (
          <span className="ml-1.5 text-[length:var(--text-xs)] font-normal text-ink-3">
            [{word.reading}]
          </span>
        )}
      </p>
      <p className="mt-1.5 text-[length:var(--text-sm)] text-ink-2">
        {word.meaning}
      </p>
    </Card>
  );
}

/** 감정 곡선: value(0~1)를 챕터 순서대로 잇는 간단한 선 그래프(accent stroke). */
function EmotionCurve({ points }: { points: EmotionPoint[] }) {
  const W = 600;
  const H = 180;
  const padX = 40;
  const padY = 34;
  const innerW = W - padX * 2;
  const innerH = H - padY * 2;
  const n = points.length;
  const x = (i: number) => (n === 1 ? W / 2 : padX + (innerW * i) / (n - 1));
  const y = (v: number) => padY + innerH * (1 - Math.max(0, Math.min(1, v)));
  const line = points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ");

  return (
    <Card padding="lg" className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-[200px] w-full min-w-[480px]"
        role="img"
        aria-label="감정 곡선"
      >
        {n > 1 && (
          <polyline
            points={line}
            fill="none"
            stroke="var(--accent)"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={x(i)} cy={y(p.value)} r={6} fill="var(--accent)" />
            <text
              x={x(i)}
              y={y(p.value) - 14}
              textAnchor="middle"
              style={{ fill: "var(--text-1)", font: "700 13px var(--font-sans)" }}
            >
              {p.label}
            </text>
            <text
              x={x(i)}
              y={H - 8}
              textAnchor="middle"
              style={{ fill: "var(--text-3)", font: "500 12px var(--font-mono)" }}
            >
              {p.chapterIdx}장
            </text>
          </g>
        ))}
      </svg>
    </Card>
  );
}
