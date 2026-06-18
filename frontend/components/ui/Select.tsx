import { cn } from "@/lib/cn";
import { Icon } from "./Icon";

/**
 * Select — 커스텀 chevron 네이티브 select(new-design_version2 forms/Select).
 * options({value,label}[]) 또는 children <option>. focus/invalid는 .ijg-control(CSS).
 */
export function Select({
  options,
  invalid = false,
  children,
  className,
  style,
  ...rest
}: {
  options?: { value: string; label: string }[];
  invalid?: boolean;
} & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
      <select
        aria-invalid={invalid || undefined}
        className={cn("ijg-control", invalid && "is-invalid", className)}
        style={{
          height: "var(--control-h)",
          padding: "0 38px 0 14px",
          appearance: "none",
          WebkitAppearance: "none",
          cursor: "pointer",
          ...style,
        }}
        {...rest}
      >
        {options
          ? options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))
          : children}
      </select>
      <Icon
        name="chevron-down"
        size={18}
        style={{
          position: "absolute",
          insetInlineEnd: 13,
          color: "var(--text-3)",
          pointerEvents: "none",
        }}
      />
    </div>
  );
}
