/**
 * 관리자 콘솔 지표 타일(new-design_version2 Metric). 값은 mono. flag면 danger + glow-red.
 */
export function Metric({
  label,
  value,
  unit,
  accent,
  flag = false,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
  unit?: React.ReactNode;
  accent?: string;
  flag?: boolean;
}) {
  return (
    <div
      className="rounded-[var(--radius-card)] border bg-surface px-[18px] py-4"
      style={{
        borderColor: flag ? "var(--danger)" : "var(--line)",
        boxShadow: flag ? "var(--glow-red)" : "var(--elev-sm)",
      }}
    >
      <p
        className="ijg-eyebrow"
        style={{ color: flag ? "var(--danger-text)" : "var(--text-3)" }}
      >
        {label}
      </p>
      <p
        className="mt-2"
        style={{
          fontFamily: "var(--font-mono)",
          fontWeight: 600,
          fontSize: 30,
          letterSpacing: "-.02em",
          color: flag ? "var(--danger-text)" : accent || "var(--text-1)",
        }}
      >
        {value}
        {unit ? (
          <span style={{ fontSize: 15, color: "var(--text-3)", marginLeft: 3 }}>
            {unit}
          </span>
        ) : null}
      </p>
    </div>
  );
}

/** 콘솔 섹션 그룹 라벨(mono eyebrow). */
export function GroupLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="ijg-eyebrow mb-3 mt-6 text-ink-3">{children}</p>
  );
}
