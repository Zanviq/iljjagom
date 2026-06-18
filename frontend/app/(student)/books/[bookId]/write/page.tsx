import { notFound, redirect } from "next/navigation";

import { CollabWriter } from "@/components/writing/CollabWriter";
import { ApiError, getBook } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function WritePage({
  params,
}: {
  params: Promise<{ bookId: string }>;
}) {
  const { bookId } = await params;
  const token = await getAccessToken();

  let book;
  try {
    book = await getBook(token, bookId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }

  // 아직 기획 단계면 기획 화면으로.
  if (book.status === "planning") redirect(`/books/${bookId}/plan`);

  // 자유집필(free) 챕터가 협업 대상. 없으면 독서로.
  const free = book.chapters.find((c) => c.mode === "free");
  if (!free) redirect(`/books/${bookId}/read`);

  return (
    <div className="mx-auto w-full max-w-[1100px] px-6 pb-16 pt-6">
      <CollabWriter bookId={bookId} chapterIdx={free.idx} />
    </div>
  );
}
