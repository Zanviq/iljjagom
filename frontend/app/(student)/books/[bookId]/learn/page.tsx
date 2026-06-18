import Link from "next/link";
import { notFound } from "next/navigation";

import { EssayForm } from "@/components/learning/EssayForm";
import { LearningOpenTracker } from "@/components/learning/LearningOpenTracker";
import { LetterForm } from "@/components/learning/LetterForm";
import { Quiz } from "@/components/learning/Quiz";
import { EmptyState } from "@/components/ui/EmptyState";
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
    <section className="mx-auto max-w-2xl">
      <LearningOpenTracker bookId={bookId} />
      <Link href={`/books/${bookId}/read`} className="text-sm font-bold text-muted">
        ← 이야기로 돌아가기
      </Link>
      <h1 className="mt-2 text-3xl font-extrabold">
        학습 활동{book.title ? ` · ${book.title}` : ""}
      </h1>
      <p className="mt-1 text-muted">이야기로 낱말도 배우고 생각도 나눠 봐요.</p>

      {isEmpty ? (
        <EmptyState className="mt-6">
          아직 학습 활동이 준비되지 않았어요. 이야기를 더 읽고 와요!
        </EmptyState>
      ) : (
        <div className="mt-6 space-y-10">
          {vocab.length > 0 && (
            <Block title="📖 낱말 카드">
              <ul className="grid gap-3 sm:grid-cols-2">
                {vocab.map((w, i) => (
                  <VocabCard key={i} word={w} />
                ))}
              </ul>
            </Block>
          )}

          {quiz.length > 0 && (
            <Block title="❓ 퀴즈">
              <Quiz items={quiz} bookId={bookId} />
            </Block>
          )}

          {essayBlanks.length > 0 && (
            <Block title="✍️ 독후감 채우기">
              <EssayForm bookId={bookId} blanks={essayBlanks} />
            </Block>
          )}

          {emotion.length > 0 && (
            <Block title="💗 감정 곡선">
              <EmotionCurve points={emotion} />
            </Block>
          )}

          <Block title="💌 인물에게 편지 쓰기">
            <LetterForm bookId={bookId} />
          </Block>
        </div>
      )}
    </section>
  );
}

function Block({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h2 className="mb-3 text-xl font-bold">{title}</h2>
      {children}
    </div>
  );
}

function VocabCard({ word }: { word: Word }) {
  return (
    <li className="rounded-card bg-surface p-4 ring-1 ring-border">
      <p className="text-lg font-bold">
        {word.term}
        {word.reading && word.reading !== word.term && (
          <span className="ml-2 text-sm font-normal text-muted">
            [{word.reading}]
          </span>
        )}
      </p>
      <p className="mt-1 text-muted">{word.meaning}</p>
    </li>
  );
}

/** 감정 곡선: value(0~1)를 챕터 순서대로 잇는 간단한 선 그래프. */
function EmotionCurve({ points }: { points: EmotionPoint[] }) {
  const W = 600;
  const H = 160;
  const padX = 30;
  const padY = 24;
  const innerW = W - padX * 2;
  const innerH = H - padY * 2;
  const n = points.length;
  const x = (i: number) => (n === 1 ? W / 2 : padX + (innerW * i) / (n - 1));
  const y = (v: number) => padY + innerH * (1 - Math.max(0, Math.min(1, v)));
  const line = points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ");

  return (
    <div className="overflow-x-auto rounded-card bg-surface p-5 ring-1 ring-border">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-40 w-full min-w-[480px]"
        role="img"
        aria-label="감정 곡선"
      >
        {n > 1 && (
          <polyline
            points={line}
            fill="none"
            stroke="var(--color-primary, #f5872e)"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
        {points.map((p, i) => (
          <g key={i}>
            <circle
              cx={x(i)}
              cy={y(p.value)}
              r={5}
              fill="var(--color-primary, #f5872e)"
            />
            <text
              x={x(i)}
              y={H - 6}
              textAnchor="middle"
              className="fill-muted text-[11px]"
            >
              {p.chapterIdx}장
            </text>
            <text
              x={x(i)}
              y={y(p.value) - 10}
              textAnchor="middle"
              className="fill-foreground text-[11px] font-bold"
            >
              {p.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
