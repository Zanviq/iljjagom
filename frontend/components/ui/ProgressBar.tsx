/**
 * ProgressBar — 읽기/완독 진척(new-design_version2 surface/ProgressBar).
 * 라운드 트랙, tone으로 fill 색. label + caption(mono) 선택.
 */
export function ProgressBar({
  value = 0,
  max = 100,
  tone = "primary",
  size = "md",
  label,
  caption,
  style,
  ...rest
}: {
  value?: number;
  max?: number;
  tone?: "primary" | "accent" | "success" | "danger";
  size?: "sm" | "md" | "lg" | number;
  label?: React.ReactNode;
  caption?: React.ReactNode;
  style?: React.CSSProperties;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "color">) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const h = typeof size === "number" ? size : { sm: 6, md: 9, lg: 14 }[size] || 9;
  const fill =
    {
      primary: "var(--primary)",
      accent: "var(--accent)",
      success: "var(--success)",
      danger: "var(--danger)",
    }[tone] || "var(--primary)";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, ...style }} {...rest}>
      {(label || caption) && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 8,
            fontSize: "var(--text-xs)",
          }}
        >
          {label && (
            <span style={{ fontWeight: 600, color: "var(--text-2)" }}>{label}</span>
          )}
          {caption && (
            <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
              {caption}
            </span>
          )}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        style={{
          height: h,
          width: "100%",
          background: "var(--surface-inset)",
          border: "var(--border-thin) solid var(--line-soft)",
          borderRadius: 999,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: fill,
            borderRadius: 999,
            transition: "width var(--dur-slow) var(--ease-env)",
          }}
        />
      </div>
    </div>
  );
}
