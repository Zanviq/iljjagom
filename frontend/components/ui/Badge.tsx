import { Icon } from "./Icon";

/**
 * Badge — 작은 상태 pill(new-design_version2 core/Badge).
 * 책 상태(기획 중/읽는 중/완독)·안전 플래그·시스템 상태에 사용.
 */
export type BadgeTone =
  | "neutral"
  | "primary"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info";

const TONES: Record<BadgeTone, { bg: string; fg: string; dot: string }> = {
  neutral: { bg: "var(--surface-inset)", fg: "var(--text-2)", dot: "var(--text-faint)" },
  primary: { bg: "var(--primary-tint)", fg: "var(--primary-text)", dot: "var(--primary)" },
  accent: { bg: "var(--accent-tint)", fg: "var(--accent-text)", dot: "var(--accent)" },
  success: { bg: "var(--success-tint)", fg: "var(--success-text)", dot: "var(--success)" },
  warning: { bg: "var(--warning-tint)", fg: "var(--warning-text)", dot: "var(--warning)" },
  danger: { bg: "var(--danger-tint)", fg: "var(--danger-text)", dot: "var(--danger)" },
  info: { bg: "var(--info-tint)", fg: "var(--info-text)", dot: "var(--info)" },
};

export function Badge({
  tone = "neutral",
  dot = false,
  icon,
  solid = false,
  children,
  style,
  ...rest
}: {
  tone?: BadgeTone;
  dot?: boolean;
  icon?: string;
  solid?: boolean;
  children?: React.ReactNode;
  style?: React.CSSProperties;
} & Omit<React.HTMLAttributes<HTMLSpanElement>, "color">) {
  const t = TONES[tone] ?? TONES.neutral;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        height: 26,
        padding: "0 11px",
        fontFamily: "var(--font-body)",
        fontSize: "var(--text-xs)",
        fontWeight: "var(--weight-bold)",
        lineHeight: 1,
        letterSpacing: "var(--tracking-snug)",
        color: solid ? "var(--on-primary)" : t.fg,
        background: solid ? t.dot : t.bg,
        borderRadius: "var(--radius-chip)",
        whiteSpace: "nowrap",
        ...style,
      }}
      {...rest}
    >
      {dot && (
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: 999,
            background: solid ? "currentColor" : t.dot,
            flex: "none",
          }}
        />
      )}
      {icon && <Icon name={icon} size={13} strokeWidth={2.5} />}
      {children}
    </span>
  );
}
