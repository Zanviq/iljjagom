import Link from "next/link";
import { notFound } from "next/navigation";

import { MidActivity } from "@/components/learning/MidActivity";
import { Icon } from "@/components/ui/Icon";
import { ApiError, getBook } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

/**
 * 중간활동 화면(04 기능개선 학생/15 §3). 기·승 협업과 전·결 읽기 사이의 필수 단계.
 * required 판정·게이트 해제는 MidActivity 클라이언트가 처리(미구현이면 읽기로 폴백).
 */
export default async function MidActivityPage({
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

  return (
    <div className="mx-auto w-full max-w-[740px] px-6 pb-20 pt-6">
      <Link
        href={`/books/${bookId}/write`}
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
        중간 활동{book.title ? ` · ${book.title}` : ""}
      </h1>
      <p className="mb-7 text-[length:var(--text-md)] text-ink-2">
        이야기의 앞부분을 돌아보고, 뒷부분을 준비해 봐요.
      </p>

      <MidActivity bookId={bookId} />
    </div>
  );
}
