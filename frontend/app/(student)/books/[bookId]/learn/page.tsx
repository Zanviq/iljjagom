import Link from "next/link";
import { notFound } from "next/navigation";

import { EmotionCurve } from "@/components/learning/EmotionCurve";
import { EmotionInput } from "@/components/learning/EmotionInput";
import { EssayForm } from "@/components/learning/EssayForm";
import { LearningOpenTracker } from "@/components/learning/LearningOpenTracker";
import { LetterForm } from "@/components/learning/LetterForm";
import { Quiz } from "@/components/learning/Quiz";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { ApiError, getBook, getLearning } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { Word } from "@/lib/types";

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

  const { vocab, quiz, essayBlanks, emotion, letterCharacters } = learning;
  // emotion: 신규 입력 틀(객체) vs 레거시 시스템 곡선(배열) 런타임 분기.
  const legacyEmotion = Array.isArray(emotion) ? emotion : null;
  const emotionFrame = Array.isArray(emotion) ? null : emotion;
  const hasEmotion = legacyEmotion
    ? legacyEmotion.length > 0
    : (emotionFrame?.points.length ?? 0) > 0;
  const isEmpty =
    vocab.length === 0 &&
    quiz.length === 0 &&
    essayBlanks.length === 0 &&
    !hasEmotion;

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

          {hasEmotion && (
            <Block icon="pen-line" title="감정 곡선">
              {emotionFrame ? (
                <EmotionInput bookId={bookId} frame={emotionFrame} />
              ) : (
                <EmotionCurve points={legacyEmotion!} />
              )}
            </Block>
          )}

          <Block icon="mail" title="인물에게 편지 쓰기">
            <LetterForm bookId={bookId} characters={letterCharacters} />
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
