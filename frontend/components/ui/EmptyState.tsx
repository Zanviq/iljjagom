import { Icon } from "./Icon";

/**
 * EmptyState — 친근한 "아직 없음" 패널(new-design_version2 feedback/EmptyState).
 * icon + title + body + action. 카피 톤은 환경에 맞춤(학생 따뜻 / 교사·관리자 plain).
 * 하위호환: children만 넘기면 본문으로 렌더(기존 호출부 유지).
 */
export function EmptyState({
  icon = "inbox",
  title,
  children,
  action,
  className,
  style,
  ...rest
}: {
  icon?: string;
  title?: React.ReactNode;
  children?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "color" | "title">) {
  return (
    <div
      className={className}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        gap: 12,
        padding: "40px 28px",
        background: "var(--surface-inset)",
        border: "var(--border) dashed var(--line-strong)",
        borderRadius: "var(--radius-card)",
        ...style,
      }}
      {...rest}
    >
      <span
        aria-hidden
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 52,
          height: 52,
          borderRadius: "calc(var(--radius-card) * 0.55)",
          background: "var(--surface-2)",
          border: "var(--border) solid var(--line)",
          color: "var(--text-faint)",
        }}
      >
        <Icon name={icon} size={24} strokeWidth={2} />
      </span>
      {title && (
        <p
          style={{
            fontSize: "var(--text-md)",
            fontWeight: 700,
            color: "var(--text-1)",
          }}
        >
          {title}
        </p>
      )}
      {children && (
        <p style={{ fontSize: "var(--text-sm)", color: "var(--text-3)", maxWidth: "32ch" }}>
          {children}
        </p>
      )}
      {action && <div style={{ marginTop: 4 }}>{action}</div>}
    </div>
  );
}
