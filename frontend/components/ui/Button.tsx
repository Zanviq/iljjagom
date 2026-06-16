import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "outline" | "ghost" | "danger";
type Size = "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-primary text-primary-foreground hover:brightness-105 active:scale-[0.98]",
  secondary:
    "bg-secondary text-white hover:brightness-105 active:scale-[0.98]",
  outline:
    "border-2 border-border bg-surface text-foreground hover:border-primary",
  ghost: "text-foreground hover:bg-black/5",
  danger: "bg-danger text-white hover:brightness-105 active:scale-[0.98]",
};

const SIZES: Record<Size, string> = {
  md: "h-12 px-5 text-base",
  lg: "h-14 px-8 text-xl",
};

export function buttonClass(
  variant: Variant = "primary",
  size: Size = "md",
  className?: string,
): string {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-card font-bold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50",
    VARIANTS[variant],
    SIZES[size],
    className,
  );
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonProps) {
  return <button className={buttonClass(variant, size, className)} {...props} />;
}
