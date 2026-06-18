import { cn } from "@/lib/cn";

/**
 * Card — 기본 표면 컨테이너(new-design_version2 surface/Card).
 * tone으로 surface 틴트, interactive면 hover lift(.ijg-card-interactive, CSS).
 * accentEdge는 좌측 4px 바 — brand 카드 금지 항목이므로 안전(danger/warning)에만.
 */
export type CardTone = "default" | "primary" | "accent" | "danger" | "warning";
export type CardPadding = "none" | "sm" | "md" | "lg" | "xl";

const PAD: Record<CardPadding, string> = {
  none: "0",
  sm: "16px",
  md: "20px",
  lg: "26px",
  xl: "32px",
};

function toneStyle(tone: CardTone, inset: boolean): { bg: string; border: string } {
  switch (tone) {
    case "primary":
      return { bg: "var(--primary-tint)", border: "var(--primary-tint)" };
    case "accent":
      return { bg: "var(--accent-tint)", border: "var(--accent-tint)" };
    case "danger":
      return { bg: "var(--danger-tint)", border: "var(--danger)" };
    case "warning":
      return { bg: "var(--warning-tint)", border: "var(--warning)" };
    default:
      return {
        bg: inset ? "var(--surface-inset)" : "var(--surface)",
        border: "var(--line)",
      };
  }
}

export function Card({
  tone = "default",
  interactive = false,
  inset = false,
  padding = "lg",
  accentEdge,
  children,
  className,
  style,
  ...rest
}: {
  tone?: CardTone;
  interactive?: boolean;
  inset?: boolean;
  padding?: CardPadding | string;
  accentEdge?: string;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "color">) {
  const pad = (PAD as Record<string, string>)[padding] ?? padding;
  const t = toneStyle(tone, inset);
  return (
    <div
      className={cn("ijg-card", interactive && "ijg-card-interactive", className)}
      style={{
        position: "relative",
        padding: pad,
        background: t.bg,
        border: `var(--border) solid ${t.border}`,
        borderRadius: "var(--radius-card)",
        overflow: "hidden",
        ...style,
      }}
      {...rest}
    >
      {accentEdge && (
        <span
          aria-hidden
          style={{
            position: "absolute",
            insetInlineStart: 0,
            top: 0,
            bottom: 0,
            width: 4,
            background: `var(--${accentEdge})`,
          }}
        />
      )}
      {children}
    </div>
  );
}
