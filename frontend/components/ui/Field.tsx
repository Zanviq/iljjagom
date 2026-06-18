/**
 * Field — label + hint + error 래퍼(new-design_version2 forms/Field).
 * 컨트롤을 children으로 전달. 간격·a11y 라벨링 일관 유지.
 */
export function Field({
  label,
  hint,
  error,
  required,
  htmlFor,
  children,
  style,
  ...rest
}: {
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  required?: boolean;
  htmlFor?: string;
  children?: React.ReactNode;
  style?: React.CSSProperties;
} & Omit<React.LabelHTMLAttributes<HTMLLabelElement>, "color">) {
  return (
    <label
      htmlFor={htmlFor}
      style={{ display: "flex", flexDirection: "column", gap: 7, ...style }}
      {...rest}
    >
      {label && (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            fontSize: "var(--text-sm)",
            fontWeight: "var(--weight-bold)",
            color: "var(--text-1)",
          }}
        >
          {label}
          {required && <span style={{ color: "var(--danger)" }}>*</span>}
        </span>
      )}
      {children}
      {error ? (
        <span
          style={{
            fontSize: "var(--text-xs)",
            fontWeight: 600,
            color: "var(--danger-text)",
          }}
        >
          {error}
        </span>
      ) : hint ? (
        <span style={{ fontSize: "var(--text-xs)", color: "var(--text-3)" }}>{hint}</span>
      ) : null}
    </label>
  );
}
