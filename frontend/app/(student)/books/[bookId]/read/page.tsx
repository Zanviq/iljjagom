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

  // 기·승(free) 협업이 아직 진행 중인 챕터가 있으면 협업 화면으로(이어읽기로 잘못 들어와도 복원).
  // 자동 생성(읽기)은 전·결(guided)에서만 일어난다(05-기능수정 §03).
  const COLLAB_TARGET = 4;
  const incompleteFree = book.chapters
    .filter((c) => c.mode === "free")
    .sort((a, b) => a.idx - b.idx)
    .find((c) => (c.paragraphCount ?? 0) < COLLAB_TARGET);
  if (incompleteFree) redirect(`/books/${bookId}/write?idx=${incompleteFree.idx}`);

  return (
    <ChapterReader
      bookId={bookId}
      title={book.title}
      totalChaptersPlanned={book.totalChaptersPlanned}
      initialChapterIdx={book.currentChapterIdx ?? undefined}
    />
  );
}
