import { notFound, redirect } from "next/navigation";

import { ChapterReader } from "@/components/reader/ChapterReader";
import { ApiError, getBook } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function ReadPage({
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

  return (
    <ChapterReader
      bookId={bookId}
      title={book.title}
      totalChaptersPlanned={book.totalChaptersPlanned}
    />
  );
}
