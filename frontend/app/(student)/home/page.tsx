import Link from "next/link";

import { buttonClass } from "@/components/ui/Button";
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
      <section>
        <Header className={null} />
        <div className="mt-6 rounded-card bg-surface p-6 ring-1 ring-border">
          <p className="text-lg font-bold">아직 학급에 들어가지 않았어요.</p>
          <p className="mt-2 text-muted">
            선생님께 받은 <strong>학급 코드</strong>로 가입하면 선생님이 낸
            이야기 주제(발제)로 새 책을 만들 수 있어요.
          </p>
        </div>
      </section>
    );
  }

  // 발제(새 책 시작)와 내 책 목록(이어 읽기)을 함께 가져온다.
  const [{ prompts }, { books }] = await Promise.all([
    getPrompts(token, me.classId),
    getBooks(token),
  ]);

  return (
    <section>
      <Header className={me.className} />

      {books.length > 0 && (
        <>
          <h2 className="mb-4 mt-8 text-xl font-bold">
            이어 읽던 이야기{" "}
            <span className="font-normal text-muted">— 만들던 책을 이어가요</span>
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2">
            {books.map((b) => (
              <BookCard key={b.id} book={b} />
            ))}
          </ul>
        </>
      )}

      <h2 className="mb-4 mt-8 text-xl font-bold">
        새 이야기 시작하기{" "}
        <span className="font-normal text-muted">— 만들고 싶은 주제를 골라요</span>
      </h2>

      {prompts.length === 0 ? (
        <div className="rounded-card bg-surface p-6 ring-1 ring-border">
          <p className="text-muted">
            아직 선생님이 낸 발제가 없어요. 조금만 기다려 주세요!
          </p>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {prompts.map((p) => (
            <PromptCard key={p.id} prompt={p} />
          ))}
        </ul>
      )}
    </section>
  );
}

function Header({ className }: { className: string | null }) {
  return (
    <div>
      <h1 className="text-3xl font-extrabold">내 책장</h1>
      <p className="mt-1 text-muted">
        {className ? `${className} ` : ""}이야기를 만들고 읽어 봐요.
      </p>
    </div>
  );
}

function PromptCard({ prompt }: { prompt: Prompt }) {
  return (
    <li className="flex flex-col rounded-card bg-surface p-5 ring-1 ring-border">
      <h3 className="text-lg font-bold">{prompt.topic}</h3>
      {prompt.learningObjectives.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2">
          {prompt.learningObjectives.map((obj, i) => (
            <li
              key={i}
              className="rounded-full bg-secondary/15 px-3 py-1 text-sm text-secondary-strong"
            >
              {obj}
            </li>
          ))}
        </ul>
      )}
      <form action={startBook} className="mt-5">
        <input type="hidden" name="promptId" value={prompt.id} />
        <SubmitButton size="md" className="w-full" pendingText="만드는 중…">
          이 주제로 새 책 만들기
        </SubmitButton>
      </form>
    </li>
  );
}

const STATUS_META: Record<
  BookStatus,
  { label: string; cta: string; href: (id: string) => string }
> = {
  planning: {
    label: "기획 중",
    cta: "기획 이어가기",
    href: (id) => `/books/${id}/plan`,
  },
  writing: {
    label: "읽는 중",
    cta: "이어 읽기",
    href: (id) => `/books/${id}/read`,
  },
  done: {
    label: "다 읽음",
    cta: "다시 읽기",
    href: (id) => `/books/${id}/read`,
  },
};

function BookCard({ book }: { book: BookSummary }) {
  const meta = STATUS_META[book.status];
  const total = book.totalChaptersPlanned;
  const progress =
    total && total > 0 ? Math.round((book.chaptersDone / total) * 100) : 0;

  return (
    <li className="flex flex-col rounded-card bg-surface p-5 ring-1 ring-border">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-lg font-bold">{book.title || "제목 짓는 중인 이야기"}</h3>
        <span className="shrink-0 rounded-full bg-accent/40 px-3 py-1 text-sm font-bold">
          {meta.label}
        </span>
      </div>

      {total && total > 0 ? (
        <div className="mt-3">
          <div className="h-2 w-full overflow-hidden rounded-full bg-black/10">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-1 text-sm text-muted">
            {book.chaptersDone} / {total}장
          </p>
        </div>
      ) : (
        <p className="mt-3 text-sm text-muted">아직 이야기를 설계하고 있어요.</p>
      )}

      <Link
        href={meta.href(book.id)}
        className={buttonClass("primary", "md", "mt-5 w-full")}
      >
        {meta.cta}
      </Link>
    </li>
  );
}
