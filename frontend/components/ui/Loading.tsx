import { cn } from "@/lib/cn";

/**
 * 로딩 문구(페이지설명 §7 톤). role="status" aria-live="polite"로 SR에 알림.
 * 무엇을 기다리는지 명시한다("이야기를 준비하는 중이에요…").
 * card=true면 흰 카드로 감싼다(읽기 전 단독 표시용).
 */
export function Loading({
  children,
  card = false,
  className,
}: {
  children: React.ReactNode;
  card?: boolean;
  className?: string;
}) {
  return (
    <p
      role="status"
      aria-live="polite"
      className={cn(
        "text-muted",
        card && "rounded-card bg-surface p-6 ring-1 ring-border",
        className,
      )}
    >
      {children}
    </p>
  );
}
