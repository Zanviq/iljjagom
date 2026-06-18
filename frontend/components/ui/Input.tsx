import { cn } from "@/lib/cn";
import { Icon } from "./Icon";

/**
 * Input — 한 줄 텍스트 필드(new-design_version2 forms/Input).
 * 선두 Lucide 아이콘 옵션. focus/invalid는 .ijg-control(CSS)로 처리(universal).
 */
export function Input({
  icon,
  invalid = false,
  className,
  style,
  ...rest
}: {
  icon?: string;
  invalid?: boolean;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  const base: React.CSSProperties = {
    height: "var(--control-h)",
    padding: "0 14px",
    ...style,
  };
  const cls = cn("ijg-control", invalid && "is-invalid", className);
  if (icon) {
    return (
      <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
        <Icon
          name={icon}
          size={18}
          style={{
            position: "absolute",
            insetInlineStart: 13,
            color: "var(--text-faint)",
            pointerEvents: "none",
          }}
        />
        <input
          aria-invalid={invalid || undefined}
          className={cls}
          style={{ ...base, paddingInlineStart: 40 }}
          {...rest}
        />
      </div>
    );
  }
  return (
    <input aria-invalid={invalid || undefined} className={cls} style={base} {...rest} />
  );
}
