import { cn } from "@/lib/cn";

/**
 * 짧은 오류 한 줄(페이지설명 §7 톤). role="alert"로 스크린리더가 즉시 읽는다.
 * 비난조 금지("…못했어요" 톤). 가능하면 다음 행동을 함께 제시.
 */
export function ErrorText({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p role="alert" className={cn("text-sm font-bold text-danger", className)}>
      {children}
    </p>
  );
}
