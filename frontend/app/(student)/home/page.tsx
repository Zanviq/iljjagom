import Link from "next/link";

import { buttonClass } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { SubmitButton } from "@/components/ui/SubmitButton";
import { getBooks, getPrompts } from "@/lib/api";
import { getCurrentMe } from "@/lib/auth/guard";
import { getAccessToken } from "@/lib/auth/server";
import { startBook } from "@/lib/books/actions";
import type { BookStatus, BookSummary, Prompt } from "@/lib/types";

export default async function StudentHomePage() {
  const me = await getCurrentMe();
  const token = await getAccessToken();

  // 학급 미가입(또는 백엔드가 classId 미반영) — 안내만.
  if (!me?.classId) {
    return (
      <div className="mx-auto w-full max-w-[var(--width-content)] px-6 pb-24 pt-9">
        <Greeting className={null} />
        <EmptyState
          icon="school"
          title="아직 학급에 들어가지 않았어요."
          className="mt-6"
        >
          선생님께 받은 학급 코드로 가입하면, 선생님이 낸 이야기 주제로 새 책을
          만들 수 있어요.
        </EmptyState>
      </div>
    );
  }

  // 발제(새 책 시작)와 내 책 목록(이어 읽기)을 함께 가져온다.
  const [{ prompts }, { books }] = await Promise.all([
    getPrompts(token, me.classId),
    getBooks(token),
  ]);

  return (
    <div className="mx-auto w-full max-w-[var(--width-content)] px-6 pb-24 pt-9">
      <Greeting className={me.className} />

      {books.length > 0 && (
        <>
          <SectionTitle
            icon="book-marked"
            title="이어 읽던 이야기"
            sub="만들던 책을 이어가요"
          />
          <div className="mb-10 flex flex-col gap-3.5">
            {books.map((b) => (
              <BookRow key={b.id} book={b} />
            ))}
          </div>
        </>
      )}

      <SectionTitle
        icon="sparkles"
        title="새 이야기 시작하기"
        sub="만들고 싶은 주제를 골라요"
      />

      {prompts.length === 0 ? (
        <EmptyState icon="sparkles" title="아직 발제가 없어요">
          아직 선생님이 낸 발제가 없어요. 조금만 기다려 주세요!
        </EmptyState>
      ) : (
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(290px,1fr))]">
          {prompts.map((p) => (
            <PromptCard key={p.id} prompt={p} />
          ))}
        </div>
      )}
    </div>
  );
}

function Greeting({ className }: { className: string | null }) {
  return (
    <div className="mb-2">
      {className && (
        <p className="ijg-eyebrow" style={{ color: "var(--primary-text)" }}>
          {className}
        </p>
      )}
      <h1
        className="mt-1.5"
        style={{
          fontFamily: "var(--font-serif)",
          fontWeight: 600,
          fontSize: 44,
          letterSpacing: "-.02em",
          color: "var(--text-1)",
        }}
      >
        안녕! 오늘도 반가워
      </h1>
      <p className="mt-1.5 text-[length:var(--text-md)] text-ink-2">
        오늘은 어떤 이야기를 만들어 볼까?
      </p>
    </div>
  );
}

function SectionTitle({
  icon,
  title,
  sub,
}: {
  icon: string;
  title: string;
  sub: string;
}) {
  return (
    <div className="mb-4 flex items-baseline gap-2.5">
      <Icon
        name={icon}
        size={20}
        strokeWidth={2.25}
        className="self-center"
        style={{ color: "var(--primary)" }}
      />
      <h2 className="text-[length:var(--text-lg)] font-extrabold text-ink">
        {title}
      </h2>
      <span className="text-[length:var(--text-sm)] text-ink-3">— {sub}</span>
    </div>
  );
}

const COVER_TONES = [
  "linear-gradient(135deg,#f6c489,#e8913a)",
  "linear-gradient(135deg,#afd0bb,#69a07e)",
  "linear-gradient(135deg,#b3b9f0,#5560d8)",
];

function coverTone(id: string): string {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
  return COVER_TONES[Math.abs(h) % COVER_TONES.length];
}

function BookCover({ id, size = 64 }: { id: string; size?: number }) {
  return (
    <span
      aria-hidden
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size * 1.18,
        flex: "none",
        borderRadius: 14,
        background: coverTone(id),
        color: "#fff",
        boxShadow: "var(--elev-sm)",
        border: "2px solid rgba(255,255,255,.35)",
      }}
    >
      <Icon name="book-open" size={Math.round(size * 0.42)} strokeWidth={1.75} />
    </span>
  );
}

const STATUS_META: Record<
  BookStatus,
  { label: string; tone: "neutral" | "primary" | "success"; cta: string; href: (id: string) => string }
> = {
  planning: {
    label: "기획 중",
    tone: "neutral",
    cta: "기획 이어가기",
    href: (id) => `/books/${id}/plan`,
  },
  writing: {
    label: "읽는 중",
    tone: "primary",
    cta: "이어 읽기",
    href: (id) => `/books/${id}/read`,
  },
  done: {
    label: "다 읽음",
    tone: "success",
    cta: "다시 읽기",
    href: (id) => `/books/${id}/read`,
  },
};

function BookRow({ book }: { book: BookSummary }) {
  const meta = STATUS_META[book.status];
  const total = book.totalChaptersPlanned;
  return (
    <Card interactive padding="md" style={{ display: "flex", gap: 16, alignItems: "center" }}>
      <BookCover id={book.id} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2.5">
          <h3
            className="truncate"
            style={{
              fontFamily: "var(--font-serif)",
              fontWeight: 600,
              fontSize: 20,
              color: "var(--text-1)",
            }}
          >
            {book.title || "제목 짓는 중인 이야기"}
          </h3>
          <Badge tone={meta.tone} dot>
            {meta.label}
          </Badge>
        </div>
        <div className="mt-3">
          {total && total > 0 ? (
            <ProgressBar
              value={book.chaptersDone}
              max={total}
              caption={`${book.chaptersDone} / ${total}장`}
            />
          ) : (
            <p className="text-[length:var(--text-sm)] text-ink-3">
              아직 이야기를 설계하고 있어요.
            </p>
          )}
        </div>
      </div>
      <Link
        href={meta.href(book.id)}
        className={buttonClass("outline", "md", "flex-none")}
      >
        {meta.cta}
        <Icon name="arrow-right" size={18} />
      </Link>
    </Card>
  );
}

function PromptCard({ prompt }: { prompt: Prompt }) {
  return (
    <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="flex items-center gap-2.5">
        <span
          className="flex h-9 w-9 items-center justify-center rounded-[10px]"
          style={{ background: "var(--accent-tint)", color: "var(--accent-text)" }}
          aria-hidden
        >
          <Icon name="lightbulb" size={19} />
        </span>
        <h3
          style={{
            fontFamily: "var(--font-serif)",
            fontWeight: 600,
            fontSize: 21,
            color: "var(--text-1)",
          }}
        >
          {prompt.topic}
        </h3>
      </div>
      {prompt.learningObjectives.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {prompt.learningObjectives.map((obj, i) => (
            <Chip key={i} icon="target">
              {obj}
            </Chip>
          ))}
        </div>
      )}
      <form action={startBook} className="mt-1">
        <input type="hidden" name="promptId" value={prompt.id} />
        <SubmitButton size="lg" icon="sparkles" fullWidth pendingText="만드는 중…">
          이 주제로 새 책 만들기
        </SubmitButton>
      </form>
    </Card>
  );
}
