import {
  Activity, ArrowLeft, ArrowRight, Bell, BookA, BookCheck, BookHeart, BookMarked,
  BookOpen, Bot, CalendarClock, ChartNoAxesColumn, Check, ChevronDown, Circle,
  CircleHelp, ClipboardCheck, Clock, Coins, Copy, Database, Download, Feather,
  FilePenLine, FileQuestion, GraduationCap, GripVertical, House, Image, Inbox,
  Languages, Layers, LayoutDashboard, LayoutGrid, Lightbulb, List, LoaderCircle,
  Lock, LogIn, LogOut, Mail, MailCheck, Megaphone, MessageCircle, MessagesSquare,
  NotebookPen, PenLine, Pencil, Plus, RefreshCw, Repeat, Save, School, ScrollText,
  Send, Settings2, ShieldAlert, ShieldCheck, SlidersHorizontal, Smile, Sparkles,
  Target, TrendingDown, TrendingUp, User, UserX, Users, Volume2, WandSparkles, X,
  type LucideProps,
} from "lucide-react";

/**
 * Icon — Lucide 라인 아이콘 래퍼(이모지 전면 대체).
 * 이름은 kebab-case("book-heart") → PascalCase(BookHeart) 매핑.
 *
 * 성능: `import * as Lucide`(배럴) 대신 **사용 아이콘만 명시 임포트**한다.
 * 런타임 문자열 조회가 있어 트리셰이킹이 불가능했고, 그 결과 lucide 전체(~1500개)가
 * 번들·컴파일되어 dev 로드·하이드레이션이 크게 느려졌다(05-기능수정 §05).
 * 아래 registry 에 없는 이름은 Circle 로 폴백하며, dev 에서 경고를 남겨 누락을 드러낸다.
 */
export type IconName = string;

const registry: Record<string, React.ComponentType<LucideProps>> = {
  Activity, ArrowLeft, ArrowRight, Bell, BookA, BookCheck, BookHeart, BookMarked,
  BookOpen, Bot, CalendarClock, ChartNoAxesColumn, Check, ChevronDown, CircleHelp,
  ClipboardCheck, Clock, Coins, Copy, Database, Download, Feather, FilePenLine,
  FileQuestion, GraduationCap, GripVertical, House, Image, Inbox, Languages, Layers,
  LayoutDashboard, LayoutGrid, Lightbulb, List, LoaderCircle, Lock, LogIn, LogOut,
  Mail, MailCheck, Megaphone, MessageCircle, MessagesSquare, NotebookPen, PenLine,
  Pencil, Plus, RefreshCw, Repeat, Save, School, ScrollText, Send, Settings2,
  ShieldAlert, ShieldCheck, SlidersHorizontal, Smile, Sparkles, Target, TrendingDown,
  TrendingUp, User, UserX, Users, Volume2, WandSparkles, X,
};

function toPascal(name: string): string {
  return name.replace(/(^|-)([a-z0-9])/g, (_, __, c: string) => c.toUpperCase());
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
  const Cmp = registry[toPascal(name)] ?? Circle;
  if (process.env.NODE_ENV !== "production" && !registry[toPascal(name)]) {
    console.warn(`[Icon] 미등록 아이콘 "${name}" → Circle 폴백. components/ui/Icon.tsx registry 에 추가하세요.`);
  }
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
