import { GroupLabel, Metric } from "@/components/admin/Metric";
import { getAdminUsage } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function AdminConsolePage() {
  const token = await getAccessToken();
  const usage = await getAdminUsage(token);

  const num = (n: number) => n.toLocaleString();

  return (
    <div>
      <div className="grid gap-3.5 [grid-template-columns:repeat(2,1fr)] sm:[grid-template-columns:repeat(4,1fr)]">
        {usage.completionRate !== undefined && (
          <Metric
            label="완독률"
            value={Math.round(usage.completionRate * 100)}
            unit="%"
            accent="var(--primary)"
          />
        )}
        {usage.revisitRate !== undefined && (
          <Metric
            label="재방문률"
            value={Math.round(usage.revisitRate * 100)}
            unit="%"
            accent="var(--accent)"
          />
        )}
        {usage.eventsTotal !== undefined && (
          <Metric label="이벤트" value={num(usage.eventsTotal)} />
        )}
        <Metric
          label="미처리 안전신호"
          value={usage.safetyFlags.open}
          unit={`/ ${usage.safetyFlags.total}`}
          flag={usage.safetyFlags.open > 0}
        />
      </div>

      <GroupLabel>사용자</GroupLabel>
      <div className="grid gap-3.5 [grid-template-columns:repeat(2,1fr)] sm:[grid-template-columns:repeat(4,1fr)]">
        <Metric label="전체" value={num(usage.users.total)} />
        <Metric label="학생" value={num(usage.users.students)} unit="명" />
        <Metric label="교사" value={usage.users.teachers} unit="명" />
        <Metric label="관리자" value={usage.users.admins} unit="명" />
      </div>

      <GroupLabel>콘텐츠</GroupLabel>
      <div className="grid gap-3.5 [grid-template-columns:repeat(2,1fr)] sm:[grid-template-columns:repeat(4,1fr)]">
        <Metric label="학급" value={num(usage.classrooms)} />
        <Metric label="발제" value={num(usage.prompts)} />
        <Metric label="책 (전체)" value={num(usage.books.total)} />
        <Metric label="집필 챕터" value={num(usage.chaptersWritten)} />
      </div>
      <div className="mt-3.5 grid gap-3.5 [grid-template-columns:repeat(3,1fr)]">
        <Metric label="기획 중" value={usage.books.planning} />
        <Metric label="집필 중" value={usage.books.writing} accent="var(--primary)" />
        <Metric label="완독" value={num(usage.books.done)} accent="var(--success-text)" />
      </div>

      {usage.learningResults && (
        <>
          <GroupLabel>학습 결과</GroupLabel>
          <div className="grid gap-3.5 [grid-template-columns:repeat(2,1fr)] sm:[grid-template-columns:repeat(4,1fr)]">
            <Metric label="퀴즈" value={num(usage.learningResults.quiz)} />
            <Metric label="독후감" value={num(usage.learningResults.essay)} />
            <Metric label="감정" value={num(usage.learningResults.emotion)} />
            <Metric label="편지" value={num(usage.learningResults.letter)} />
          </div>
        </>
      )}
    </div>
  );
}
