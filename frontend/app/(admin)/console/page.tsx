import { getAdminUsage } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function AdminConsolePage() {
  const token = await getAccessToken();
  const usage = await getAdminUsage(token);

  return (
    <section>
      <h1 className="text-3xl font-extrabold">운영 콘솔</h1>
      <p className="mt-1 text-muted">사용량과 안전 신호를 모니터링해요.</p>

      <h2 className="mb-3 mt-8 text-lg font-bold">사용자</h2>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="전체" value={usage.users.total} />
        <Stat label="학생" value={usage.users.students} />
        <Stat label="교사" value={usage.users.teachers} />
        <Stat label="관리자" value={usage.users.admins} />
      </dl>

      <h2 className="mb-3 mt-8 text-lg font-bold">콘텐츠</h2>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="학급" value={usage.classrooms} />
        <Stat label="발제" value={usage.prompts} />
        <Stat label="책(전체)" value={usage.books.total} />
        <Stat label="집필 챕터" value={usage.chaptersWritten} />
      </dl>
      <dl className="mt-3 grid grid-cols-3 gap-3">
        <Stat label="기획 중" value={usage.books.planning} />
        <Stat label="집필 중" value={usage.books.writing} />
        <Stat label="완독" value={usage.books.done} />
      </dl>

      <h2 className="mb-3 mt-8 text-lg font-bold">안전 신호</h2>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat
          label="미처리"
          value={usage.safetyFlags.open}
          highlight={usage.safetyFlags.open > 0}
        />
        <Stat label="전체" value={usage.safetyFlags.total} />
      </dl>
    </section>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-card p-4 ring-1 ${
        highlight
          ? "bg-danger/10 ring-danger"
          : "bg-surface ring-border"
      }`}
    >
      <dt className="text-xs font-bold text-muted">{label}</dt>
      <dd
        className={`mt-1 text-2xl font-extrabold ${
          highlight ? "text-danger" : ""
        }`}
      >
        {value}
      </dd>
    </div>
  );
}
