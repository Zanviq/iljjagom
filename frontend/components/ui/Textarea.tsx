import { cn } from "@/lib/cn";

/**
 * Textarea — 여러 줄 입력(new-design_version2 forms/Textarea).
 * 편지·독후감·이야기 고치기 요청에 사용. focus/invalid는 .ijg-control(CSS).
 */
export function Textarea({
  invalid = false,
  rows = 4,
  className,
  style,
  ...rest
}: {
  invalid?: boolean;
} & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      rows={rows}
      aria-invalid={invalid || undefined}
      className={cn("ijg-control", invalid && "is-invalid", className)}
      style={{
        padding: "12px 14px",
        lineHeight: "var(--leading-normal)",
        resize: "vertical",
        ...style,
      }}
      {...rest}
    />
  );
}
