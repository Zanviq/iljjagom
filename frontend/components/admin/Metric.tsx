import Link from "next/link";

interface MetricProps {
  label: React.ReactNode;
  value: React.ReactNode;
  unit?: React.ReactNode;
  accent?: string;
  flag?: boolean;
}

/**
 * 관리자 콘솔 지표 타일(new-design_version2 Metric). 값은 mono. flag면 danger + glow-red.
 */
export function Metric({
  label,
  value,
  unit,
  accent,
  flag = false,
}: MetricProps) {
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

/** 클릭 가능한 지표 타일 — 누르면 그 숫자를 구성하는 목록으로(관리자/01 죽은 숫자 제거). */
export function MetricLink({ href, ...props }: { href: string } & MetricProps) {
  return (
    <Link
      href={href}
      className="block rounded-[var(--radius-card)] transition hover:-translate-y-0.5 hover:brightness-105"
    >
      <Metric {...props} />
    </Link>
  );
}

/** 콘솔 섹션 그룹 라벨(mono eyebrow). */
export function GroupLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="ijg-eyebrow mb-3 mt-6 text-ink-3">{children}</p>
  );
}
