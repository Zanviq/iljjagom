import Link from "next/link";
import { notFound } from "next/navigation";

import { DashboardTrend } from "@/components/teacher/DashboardTrend";
import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatCard } from "@/components/ui/StatCard";
import { ApiError, getClasses, getDashboard } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { BookStatus, DashboardStudent } from "@/lib/types";

const STATUS_LABEL: Record<BookStatus, string> = {
  planning: "기획 중",
  writing: "집필 중",
  done: "완독",
};
const STATUS_TONE: Record<BookStatus, "neutral" | "primary" | "success"> = {
  planning: "neutral",
  writing: "primary",
  done: "success",
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
  const hasExtra =
    summary.revisitRate !== undefined ||
    summary.vocabQuizAccuracy !== undefined ||
    summary.essaysSubmitted !== undefined;

  return (
    <div>
      <TeacherHeader
        title={`대시보드${klass ? ` · ${klass.name}` : ""}`}
        sub="학급의 진척과 완독률을 한눈에 봐요."
      />

      <div className="mb-3.5 grid grid-cols-2 gap-3.5 sm:grid-cols-4">
        <StatCard label="학생" value={summary.studentCount} unit="명" icon="users" />
        <StatCard
          label="시작한 책"
          value={summary.booksStarted}
          unit="권"
          icon="book-open"
        />
        <StatCard
          label="완독"
          value={summary.booksDone}
          unit="권"
          sub={`완독률 ${completionPct}%`}
          icon="book-check"
        />
        <StatCard
          label="배운 낱말"
          value={summary.vocabCount}
          unit="개"
          icon="book-a"
        />
      </div>

      {hasExtra && (
        <div className="mb-7 grid grid-cols-2 gap-3.5 sm:grid-cols-3">
          {summary.revisitRate !== undefined && (
            <StatCard
              label="재방문률"
              value={Math.round(summary.revisitRate * 100)}
              unit="%"
              icon="repeat"
            />
          )}
          {summary.vocabQuizAccuracy !== undefined && (
            <StatCard
              label="어휘 정답률"
              value={Math.round(summary.vocabQuizAccuracy * 100)}
              unit="%"
              icon="target"
            />
          )}
          {summary.essaysSubmitted !== undefined && (
            <StatCard
              label="독후감 제출"
              value={summary.essaysSubmitted}
              unit="개"
              icon="pen-line"
            />
          )}
        </div>
      )}

      <DashboardTrend classId={classId} />

      {summary.objectiveAchievement &&
        summary.objectiveAchievement.length > 0 && (
          <>
            <h2 className="mb-1.5 text-[length:var(--text-md)] font-extrabold text-ink">
              학습목표 달성률
            </h2>
            <Card padding="lg" className="mb-7">
              {summary.objectiveAchievement.map((o, i) => {
                const pct = Math.round(o.rate * 100);
                return (
                  <div
                    key={i}
                    className="flex items-center gap-3.5 border-b border-line-soft py-2.5 last:border-0"
                  >
                    <span className="w-[180px] flex-none text-[length:var(--text-sm)] font-semibold text-ink">
                      {o.objective}
                    </span>
                    <div className="flex-1">
                      <ProgressBar
                        value={pct}
                        tone={pct >= 70 ? "success" : pct >= 50 ? "primary" : "danger"}
                      />
                    </div>
                    <span
                      className="w-11 flex-none text-right font-semibold text-ink"
                      style={{ fontFamily: "var(--font-mono)", fontSize: 14 }}
                    >
                      {pct}%
                    </span>
                  </div>
                );
              })}
            </Card>
          </>
        )}

      <h2 className="mb-3 text-[length:var(--text-md)] font-extrabold text-ink">
        학생별 진척
      </h2>
      {students.length === 0 ? (
        <EmptyState icon="users" title="아직 학급에 학생이 없어요">
          학생이 가입 코드로 들어오면 진척이 표시돼요.
        </EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-[var(--radius-card)] border border-line">
          <table className="w-full min-w-[32rem] border-collapse bg-surface text-left">
            <thead>
              <tr className="border-b border-line bg-surface-2">
                {["학생", "이야기", "상태", "진행률"].map((h) => (
                  <th
                    key={h}
                    className="ijg-eyebrow p-3 text-ink-3"
                    style={{ textAlign: "left" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <StudentRow key={s.studentId} classId={classId} student={s} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StudentRow({
  classId,
  student,
}: {
  classId: string;
  student: DashboardStudent;
}) {
  const total = student.totalChapters;
  const hasBook = student.bookId !== null && student.status !== null;

  return (
    <tr className="border-b border-line-soft last:border-0">
      <td className="p-3">
        <Link
          href={`/classes/${classId}/students/${student.studentId}`}
          className="flex items-center gap-2.5 hover:underline"
        >
          <Avatar name={student.studentEmail} size={30} />
          <span className="text-[length:var(--text-sm)] font-semibold text-ink">
            {student.studentEmail}
          </span>
        </Link>
      </td>
      <td className="p-3 text-[length:var(--text-sm)]">
        {hasBook ? (
          student.title || <span className="text-ink-faint">제목 짓는 중</span>
        ) : (
          <span className="text-ink-faint">아직 시작 안 함</span>
        )}
      </td>
      <td className="p-3">
        {student.status ? (
          <Badge tone={STATUS_TONE[student.status]} dot>
            {STATUS_LABEL[student.status]}
          </Badge>
        ) : (
          <span className="text-ink-faint">—</span>
        )}
      </td>
      <td className="p-3">
        {hasBook ? (
          <div className="flex items-center gap-2.5">
            <div className="w-[110px]">
              <ProgressBar value={student.chaptersDone} max={total || 1} size="sm" />
            </div>
            <span
              className="text-ink-3"
              style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}
            >
              {student.chaptersDone}/{total || "?"}
            </span>
          </div>
        ) : (
          <span className="text-ink-faint">—</span>
        )}
      </td>
    </tr>
  );
}
