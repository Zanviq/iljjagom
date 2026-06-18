import { Icon } from "./Icon";

/**
 * Chip — 선택/삭제 가능한 태그(new-design_version2 core/Chip).
 * 학습 목표·필터·어휘 표시. selected=true면 채움(accent).
 */
export function Chip({
  selected = false,
  icon,
  onRemove,
  children,
  style,
  ...rest
}: {
  selected?: boolean;
  icon?: string;
  onRemove?: (e: React.MouseEvent) => void;
  children?: React.ReactNode;
  style?: React.CSSProperties;
} & React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        height: 32,
        padding: onRemove ? "0 6px 0 13px" : "0 14px",
        fontFamily: "var(--font-body)",
        fontSize: "var(--text-sm)",
        fontWeight: "var(--weight-semibold)",
        color: selected ? "var(--on-accent)" : "var(--accent-text)",
        background: selected ? "var(--accent)" : "var(--accent-tint)",
        border: `var(--border) solid ${selected ? "transparent" : "var(--accent-tint)"}`,
        borderRadius: "var(--radius-chip)",
        cursor: rest.onClick ? "pointer" : "default",
        transition: "var(--transition-base)",
        whiteSpace: "nowrap",
        ...style,
      }}
      {...rest}
    >
      {icon && <Icon name={icon} size={14} strokeWidth={2.5} />}
      {children}
      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove(e);
          }}
          aria-label="삭제"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 20,
            height: 20,
            padding: 0,
            border: "none",
            borderRadius: 999,
            background: "transparent",
            color: "inherit",
            opacity: 0.7,
          }}
        >
          <Icon name="x" size={14} strokeWidth={2.5} />
        </button>
      )}
    </span>
  );
}
