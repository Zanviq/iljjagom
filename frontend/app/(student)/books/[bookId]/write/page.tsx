import { notFound, redirect } from "next/navigation";

import { CollabWriter } from "@/components/writing/CollabWriter";
import { ApiError, getBook } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

// 한 free 챕터의 협업 완료 기준 문단 수(백엔드 COLLAB_TARGET_PARAGRAPHS 와 동일).
const COLLAB_TARGET = 4;

export default async function WritePage({
  params,
  searchParams,
}: {
  params: Promise<{ bookId: string }>;
  searchParams: Promise<{ idx?: string }>;
}) {
  const { bookId } = await params;
  const { idx } = await searchParams;
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

  const freeChapters = book.chapters
    .filter((c) => c.mode === "free")
    .sort((a, b) => a.idx - b.idx);

  // ?idx= 가 free 챕터를 가리키면 그 챕터, 아니면 첫 '미완' free 챕터(기·승 순차).
  const wanted = Number(idx);
  const target =
    freeChapters.find((c) => c.idx === wanted) ??
    freeChapters.find((c) => (c.paragraphCount ?? 0) < COLLAB_TARGET);

  // 협업할 free 챕터가 없으면(모두 완료) 독서로.
  if (!target) redirect(`/books/${bookId}/read`);

  return (
    <div className="mx-auto w-full max-w-[1100px] px-6 pb-16 pt-6">
      <CollabWriter bookId={bookId} chapterIdx={target.idx} />
    </div>
  );
}
