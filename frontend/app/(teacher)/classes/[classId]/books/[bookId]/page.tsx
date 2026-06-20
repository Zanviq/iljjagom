import Link from "next/link";
import { notFound } from "next/navigation";

import { StudentWorkViewer } from "@/components/teacher/StudentWorkViewer";
import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { Icon } from "@/components/ui/Icon";
import { ApiError, getBook } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function StudentBookPage({
  params,
}: {
  params: Promise<{ classId: string; bookId: string }>;
}) {
  const { classId, bookId } = await params;
  const token = await getAccessToken();

  let book;
  try {
    book = await getBook(token, bookId);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 403)) {
      notFound();
    }
    throw e;
  }

  return (
    <div>
      <Link
        href={`/classes/${classId}/dashboard`}
        className="inline-flex items-center gap-1.5 py-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
      >
        <Icon name="arrow-left" size={16} />
        대시보드
      </Link>
      <TeacherHeader
        title={book.title || "학생 이야기"}
        sub="학생 작성물 · 읽기 전용"
      />
      <StudentWorkViewer bookId={bookId} />
    </div>
  );
}
