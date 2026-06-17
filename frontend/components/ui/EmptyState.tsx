import { cn } from "@/lib/cn";

/**
 * 빈 상태 표준 카드(페이지설명 §7 톤). 친근한 회색 안내.
 * 예) <EmptyState>아직 선생님이 낸 발제가 없어요.</EmptyState>
 */
export function EmptyState({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-card bg-surface p-6 text-center text-muted ring-1 ring-border",
        className,
      )}
    >
      {children}
    </div>
  );
}
