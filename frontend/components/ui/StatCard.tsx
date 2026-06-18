import { Icon } from "./Icon";

/**
 * StatCard — 단일 지표 타일(new-design_version2 surface/StatCard).
 * 교사 대시보드·관리자 콘솔의 backbone. 숫자는 mono. tone="danger"는 주의 플래그.
 */
export function StatCard({
  label,
  value,
  unit,
  sub,
  icon,
  tone = "default",
  trend,
  style,
  ...rest
}: {
  label: React.ReactNode;
  value: React.ReactNode;
  unit?: React.ReactNode;
  sub?: React.ReactNode;
  icon?: string;
  tone?: "default" | "danger";
  trend?: number;
  style?: React.CSSProperties;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "color">) {
  const flagged = tone === "danger";
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 10,
        padding: "18px 20px",
        background: flagged ? "var(--danger-tint)" : "var(--surface)",
        border: `var(--border) solid ${flagged ? "var(--danger)" : "var(--line)"}`,
        borderRadius: "var(--radius-card)",
        boxShadow: "var(--elev-sm)",
        ...style,
      }}
      {...rest}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <span
          className="ijg-eyebrow"
          style={{ color: flagged ? "var(--danger-text)" : "var(--text-3)" }}
        >
          {label}
        </span>
        {icon && (
          <Icon
            name={icon}
            size={16}
            strokeWidth={2.25}
            style={{ color: flagged ? "var(--danger)" : "var(--text-faint)" }}
          />
        )}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-2xl)",
            fontWeight: "var(--weight-semibold)",
            lineHeight: 1,
            letterSpacing: "var(--tracking-tight)",
            color: flagged ? "var(--danger-text)" : "var(--text-1)",
          }}
        >
          {value}
        </span>
        {unit && (
          <span
            style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-3)" }}
          >
            {unit}
          </span>
        )}
        {trend != null && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 2,
              marginInlineStart: "auto",
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-xs)",
              fontWeight: 600,
              color: trend >= 0 ? "var(--success-text)" : "var(--danger-text)",
            }}
          >
            <Icon
              name={trend >= 0 ? "trending-up" : "trending-down"}
              size={13}
              strokeWidth={2.5}
            />
            {trend >= 0 ? "+" : ""}
            {trend}%
          </span>
        )}
      </div>
      {sub && (
        <span style={{ fontSize: "var(--text-xs)", color: "var(--text-3)" }}>{sub}</span>
      )}
    </div>
  );
}
