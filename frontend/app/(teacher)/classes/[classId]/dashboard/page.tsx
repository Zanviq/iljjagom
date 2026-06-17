import Link from "next/link";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/ui/EmptyState";
import { ApiError, getClasses, getDashboard } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { BookStatus, DashboardStudent } from "@/lib/types";

const STATUS_LABEL: Record<BookStatus, string> = {
  planning: "기획 중",
  writing: "집필 중",
  done: "완독",
};

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ classId: string }>;
}) {
  const { classId } = await params;
  const token = await getAccessToken();

  const [{ classes }, dashboard] = await Promise.all([
    getClasses(token),
    getDashboard(token, classId).catch((e) => {
      if (e instanceof ApiError && (e.status === 404 || e.status === 403)) {
        notFound();
      }
      throw e;
    }),
  ]);

  const klass = classes.find((c) => c.id === classId);
  const { students, summary } = dashboard;
  const completionPct = Math.round(summary.completionRate * 100);

  return (
    <section>
      <Link href="/classes" className="text-sm font-bold text-muted">
        ← 학급 목록
      </Link>
      <h1 className="mt-2 text-3xl font-extrabold">
        대시보드 {klass ? `· ${klass.name}` : ""}
      </h1>
      <p className="mt-1 text-muted">학급의 진척과 완독률을 한눈에 봐요.</p>

      <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryCard label="학생" value={`${summary.studentCount}명`} />
        <SummaryCard label="시작한 책" value={`${summary.booksStarted}권`} />
        <SummaryCard
          label="완독"
          value={`${summary.booksDone}권`}
          sub={`완독률 ${completionPct}%`}
        />
        <SummaryCard label="배운 낱말" value={`${summary.vocabCount}개`} />
      </dl>

      <h2 className="mb-3 mt-8 text-lg font-bold">학생별 진척</h2>
      {students.length === 0 ? (
        <EmptyState>아직 학급에 학생이 없어요.</EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-card ring-1 ring-border">
          <table className="w-full min-w-[32rem] border-collapse bg-surface text-left">
            <thead>
              <tr className="border-b border-border text-sm text-muted">
                <th className="p-3 font-bold">학생</th>
                <th className="p-3 font-bold">이야기</th>
                <th className="p-3 font-bold">상태</th>
                <th className="p-3 font-bold">진행률</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <StudentRow key={s.studentId} student={s} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function SummaryCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-card bg-surface p-4 ring-1 ring-border">
      <dt className="text-xs font-bold text-muted">{label}</dt>
      <dd className="mt-1 text-2xl font-extrabold">{value}</dd>
      {sub && <dd className="text-xs text-secondary">{sub}</dd>}
    </div>
  );
}

function StudentRow({ student }: { student: DashboardStudent }) {
  const total = student.totalChapters;
  const pct = total > 0 ? Math.round((student.chaptersDone / total) * 100) : 0;
  const hasBook = student.bookId !== null && student.status !== null;

  return (
    <tr className="border-b border-border last:border-0">
      <td className="p-3 font-medium">{student.studentEmail}</td>
      <td className="p-3">
        {hasBook ? (
          student.title || (
            <span className="text-muted">제목 짓는 중</span>
          )
        ) : (
          <span className="text-muted">아직 시작 안 함</span>
        )}
      </td>
      <td className="p-3">
        {student.status ? (
          <span className="rounded-full bg-accent/40 px-2.5 py-0.5 text-sm font-bold">
            {STATUS_LABEL[student.status]}
          </span>
        ) : (
          <span className="text-muted">—</span>
        )}
      </td>
      <td className="p-3">
        {hasBook ? (
          <div className="flex items-center gap-2">
            <div className="h-2 w-24 overflow-hidden rounded-full bg-black/10">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-sm text-muted">
              {student.chaptersDone}/{total || "?"}
            </span>
          </div>
        ) : (
          <span className="text-muted">—</span>
        )}
      </td>
    </tr>
  );
}
