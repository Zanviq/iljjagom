import Link from "next/link";

import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { getStudentBooks } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { BookStatus, BookSummary } from "@/lib/types";

const STATUS_META: Record<
  BookStatus,
  { label: string; tone: "neutral" | "primary" | "success" }
> = {
  planning: { label: "기획 중", tone: "neutral" },
  writing: { label: "집필 중", tone: "primary" },
  done: { label: "완독", tone: "success" },
};

export default async function StudentBooksPage({
  params,
}: {
  params: Promise<{ classId: string; studentId: string }>;
}) {
  const { classId, studentId } = await params;
  const token = await getAccessToken();

  let books: BookSummary[] = [];
  let unavailable = false;
  try {
    books = (await getStudentBooks(token, classId, studentId)).books;
  } catch {
    unavailable = true;
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
      <TeacherHeader title="학생 이야기" sub="이 학생이 만든 책을 골라 열람해요." />

      {unavailable ? (
        <EmptyState icon="user" title="학생 자료를 준비하고 있어요">
          잠시 후 다시 확인해 주세요.
        </EmptyState>
      ) : books.length === 0 ? (
        <EmptyState icon="book-open" title="아직 만든 책이 없어요">
          학생이 이야기를 시작하면 여기에 보여요.
        </EmptyState>
      ) : (
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(300px,1fr))]">
          {books.map((b) => {
            const meta = STATUS_META[b.status];
            return (
              <Link key={b.id} href={`/classes/${classId}/books/${b.id}`} className="block">
                <Card interactive padding="lg" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div className="flex items-start justify-between gap-2">
                    <h3
                      className="truncate"
                      style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 19, color: "var(--text-1)" }}
                    >
                      {b.title || "제목 짓는 중"}
                    </h3>
                    {meta && (
                      <Badge tone={meta.tone} dot>
                        {meta.label}
                      </Badge>
                    )}
                  </div>
                  <p
                    className="text-ink-3"
                    style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}
                  >
                    {b.chaptersDone}
                    {b.totalChaptersPlanned ? ` / ${b.totalChaptersPlanned}` : ""}장
                  </p>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
