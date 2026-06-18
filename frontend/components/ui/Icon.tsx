import * as Lucide from "lucide-react";
import type { LucideProps } from "lucide-react";

/**
 * Icon — Lucide 라인 아이콘 래퍼(이모지 전면 대체).
 * 원본 디자인의 `core/Icon.jsx`(data-lucide 플레이스홀더 + createIcons)를
 * SSR 환경에 맞게 lucide-react 컴포넌트로 1:1 치환.
 * 이름은 kebab-case("book-heart") → PascalCase(BookHeart) 매핑.
 */
export type IconName = string;

const registry = Lucide as unknown as Record<
  string,
  React.ComponentType<LucideProps>
>;

function toPascal(name: string): string {
  return name.replace(/(^|-)([a-z0-9])/g, (_, __, c: string) =>
    c.toUpperCase(),
  );
}

export function Icon({
  name,
  size = 20,
  strokeWidth = 2,
  className,
  style,
  ...rest
}: {
  name: IconName;
  size?: number;
  strokeWidth?: number;
  className?: string;
  style?: React.CSSProperties;
} & Omit<LucideProps, "ref">) {
  const Cmp = registry[toPascal(name)] ?? Lucide.Circle;
  return (
    <Cmp
      size={size}
      strokeWidth={strokeWidth}
      className={className}
      style={{ flex: "none", ...style }}
      aria-hidden
      {...rest}
    />
  );
}
