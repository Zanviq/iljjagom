import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { PlanChat } from "@/components/planning/PlanChat";
import { Icon } from "@/components/ui/Icon";
import { ApiError, getBook } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function PlanPage({
  params,
}: {
  params: Promise<{ bookId: string }>;
}) {
  const { bookId } = await params;
  const token = await getAccessToken();

  let status: string;
  try {
    const book = await getBook(token, bookId);
    status = book.status;
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }

  // 이미 집필이 시작된 책이면 독서 화면으로.
  if (status !== "planning") redirect(`/books/${bookId}/read`);

  return (
    <div className="mx-auto w-full max-w-[var(--width-content)] px-6 pb-10 pt-6">
      <Link
        href="/home"
        className="inline-flex items-center gap-1.5 py-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
      >
        <Icon name="arrow-left" size={16} />
        내 책장
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
        이야기 만들기
      </h1>
      <p className="mb-6 text-[length:var(--text-md)] text-ink-2">
        곰 작가와 이야기를 나누며 주인공을 만들어요.
      </p>
      <PlanChat bookId={bookId} />
    </div>
  );
}
