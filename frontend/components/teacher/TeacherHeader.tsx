/**
 * 교사 콘텐츠 헤더(new-design_version2 TeacherHeader): 제목 + 서브 + 우측 액션 슬롯.
 */
export function TeacherHeader({
  title,
  sub,
  action,
}: {
  title: React.ReactNode;
  sub?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex items-end justify-between gap-4">
      <div>
        <h1
          className="text-[length:var(--text-xl)] font-extrabold text-ink"
          style={{ letterSpacing: "-.01em" }}
        >
          {title}
        </h1>
        {sub && <p className="mt-1 text-[length:var(--text-sm)] text-ink-2">{sub}</p>}
      </div>
      {action}
    </div>
  );
}
