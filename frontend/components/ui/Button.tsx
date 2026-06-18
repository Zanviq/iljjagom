import { cn } from "@/lib/cn";
import { Icon } from "./Icon";

/**
 * Button — 디자인 시스템 액션 프리미티브(new-design_version2 core/Button).
 * 테마 토큰으로 자동 re-skin. hover/active는 components.css(.ijg-btn*)에서 CSS로 처리해
 * 서버/클라이언트 어디서나 쓰인다.
 * 하위호환: variant "primary"=solid, "secondary"=accent (기존 호출부 유지용).
 */
export type ButtonVariant =
  | "solid"
  | "accent"
  | "outline"
  | "ghost"
  | "danger"
  | "primary"
  | "secondary";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  solid: "ijg-btn-solid",
  primary: "ijg-btn-solid",
  accent: "ijg-btn-accent",
  secondary: "ijg-btn-accent",
  outline: "ijg-btn-outline",
  ghost: "ijg-btn-ghost",
  danger: "ijg-btn-danger",
};

const SIZE_CLASS: Record<ButtonSize, string> = {
  sm: "h-[var(--control-h-sm)] px-4 gap-1.5 text-[length:var(--text-sm)]",
  md: "h-[var(--control-h)] px-[22px] gap-2 text-[length:var(--text-base)]",
  lg: "h-[var(--control-h-lg)] px-8 gap-2.5 text-[length:var(--text-md)]",
};

const ICON_SIZE: Record<ButtonSize, number> = { sm: 16, md: 18, lg: 20 };

export function buttonClass(
  variant: ButtonVariant = "solid",
  size: ButtonSize = "md",
  className?: string,
): string {
  return cn("ijg-btn", VARIANT_CLASS[variant], SIZE_CLASS[size], className);
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: string;
  iconRight?: string;
  fullWidth?: boolean;
  loading?: boolean;
}

export function Button({
  variant = "solid",
  size = "md",
  icon,
  iconRight,
  fullWidth = false,
  loading = false,
  disabled = false,
  className,
  children,
  ...rest
}: ButtonProps) {
  const isz = ICON_SIZE[size];
  return (
    <button
      disabled={disabled || loading}
      className={cn(buttonClass(variant, size), fullWidth && "w-full", className)}
      {...rest}
    >
      {loading ? (
        <Icon name="loader-circle" size={isz} className="animate-spin" />
      ) : (
        icon && <Icon name={icon} size={isz} />
      )}
      {children}
      {iconRight && !loading && <Icon name={iconRight} size={isz} />}
    </button>
  );
}
