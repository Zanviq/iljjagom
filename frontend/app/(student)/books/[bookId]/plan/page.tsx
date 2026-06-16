import { notFound, redirect } from "next/navigation";

import { PlanChat } from "@/components/planning/PlanChat";
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
    <section>
      <h1 className="text-3xl font-extrabold">이야기 만들기</h1>
      <p className="mb-6 mt-1 text-muted">
        AI 친구와 이야기하며 주인공과 배경을 정해요.
      </p>
      <PlanChat bookId={bookId} />
    </section>
  );
}
