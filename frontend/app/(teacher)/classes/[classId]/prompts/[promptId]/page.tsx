import Link from "next/link";

import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatCard } from "@/components/ui/StatCard";
import { getPromptSubmissions } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type {
  BookStatus,
  PromptSubmission,
  PromptSubmissionsResponse,
} from "@/lib/types";

const STATUS_META: Record<
  BookStatus,
  { label: string; tone: "neutral" | "primary" | "success" }
> = {
  planning: { label: "기획 중", tone: "neutral" },
  writing: { label: "집필 중", tone: "primary" },
  done: { label: "완독", tone: "success" },
};

export default async function PromptDetailPage({
  params,
}: {
  params: Promise<{ classId: string; promptId: string }>;
}) {
  const { classId, promptId } = await params;
  const token = await getAccessToken();

  let data: PromptSubmissionsResponse | null = null;
  try {
    data = await getPromptSubmissions(token, classId, promptId);
  } catch {
    data = null;
  }

  const back = (
    <Link
      href={`/classes/${classId}/prompt`}
      className="inline-flex items-center gap-1.5 py-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
    >
      <Icon name="arrow-left" size={16} />
      발제 목록
    </Link>
  );

  if (!data) {
    return (
      <div>
        {back}
        <TeacherHeader title="발제 상세" sub="발제별 참여·작성 현황" />
        <EmptyState icon="file-question" title="집계를 준비하고 있어요">
          잠시 후 다시 확인해 주세요.
        </EmptyState>
      </div>
    );
  }

  const { prompt, counts, submissions, notStarted } = data;

  return (
    <div>
      {back}
      <TeacherHeader
        title={prompt.topic}
        sub={prompt.learningObjectives.join(" · ") || "발제별 참여·작성 현황"}
      />

      <div className="mb-7 grid grid-cols-2 gap-3.5 sm:grid-cols-3">
        <StatCard label="참여" value={counts.started} unit={`/ ${counts.enrolled}명`} icon="users" />
        <StatCard label="완독" value={counts.finished} unit="명" icon="book-check" />
        <StatCard label="미시작" value={notStarted.length} unit="명" icon="user-x" />
      </div>

      <h2 className="mb-3 text-[length:var(--text-md)] font-extrabold text-ink">
        참여 학생
      </h2>
      {submissions.length === 0 ? (
        <EmptyState icon="users" title="아직 참여한 학생이 없어요">
          학생이 이 발제로 책을 만들면 여기에 보여요.
        </EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-[var(--radius-card)] border border-line">
          <table className="w-full min-w-[44rem] border-collapse bg-surface text-left">
            <thead>
              <tr className="border-b border-line bg-surface-2">
                {["학생", "이야기", "상태", "진행", "작성"].map((h) => (
                  <th key={h} className="ijg-eyebrow p-3 text-ink-3" style={{ textAlign: "left" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {submissions.map((s) => (
                <SubmissionRow key={s.studentId} classId={classId} sub={s} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {notStarted.length > 0 && (
        <>
          <h2 className="mb-3 mt-8 text-[length:var(--text-md)] font-extrabold text-ink">
            아직 시작 안 함 ({notStarted.length})
          </h2>
          <div className="flex flex-wrap gap-2">
            {notStarted.map((n) => (
              <span
                key={n.studentId}
                className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-3 py-1.5 text-[length:var(--text-sm)] text-ink-2"
              >
                <Avatar name={n.studentEmail} size={22} />
                {n.studentEmail}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function SubmissionRow({
  classId,
  sub,
}: {
  classId: string;
  sub: PromptSubmission;
}) {
  const meta = STATUS_META[sub.status];
  const total = sub.totalChaptersPlanned;
  return (
    <tr className="border-b border-line-soft last:border-0">
      <td className="p-3">
        <Link
          href={`/classes/${classId}/books/${sub.bookId}`}
          className="flex items-center gap-2.5 hover:underline"
        >
          <Avatar name={sub.studentEmail} size={30} />
          <span className="text-[length:var(--text-sm)] font-semibold text-ink">
            {sub.studentEmail}
          </span>
        </Link>
      </td>
      <td className="p-3 text-[length:var(--text-sm)]">
        {sub.title || <span className="text-ink-faint">제목 짓는 중</span>}
      </td>
      <td className="p-3">
        {meta && (
          <Badge tone={meta.tone} dot>
            {meta.label}
          </Badge>
        )}
      </td>
      <td className="p-3">
        <div className="flex items-center gap-2.5">
          <div className="w-[90px]">
            <ProgressBar value={sub.chaptersDone} max={total || 1} size="sm" />
          </div>
          <span className="text-ink-3" style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
            {sub.chaptersDone}/{total || "?"}
          </span>
        </div>
      </td>
      <td className="p-3">
        <div className="flex flex-wrap gap-1.5 text-[length:var(--text-xs)] text-ink-3">
          <span title="작성 글자">{sub.charTotal}자</span>
          {sub.quizCount > 0 && <span>· 퀴즈 {sub.quizCount}</span>}
          {sub.essayCount > 0 && <span>· 독후감 {sub.essayCount}</span>}
          {sub.letterCount > 0 && <span>· 편지 {sub.letterCount}</span>}
          {sub.emotionLogged && <span>· 감정</span>}
        </div>
      </td>
    </tr>
  );
}
