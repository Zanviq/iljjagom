import Link from "next/link";

import { BookTimeline } from "@/components/admin/BookTimeline";
import { Icon } from "@/components/ui/Icon";

/**
 * 책 단계별 통합 타임라인 페이지(04 기능개선 관리자/01). 사용자 드릴다운의 책 카드에서 진입.
 */
export default async function ConsoleBookTimelinePage({
  params,
}: {
  params: Promise<{ bookId: string }>;
}) {
  const { bookId } = await params;

  return (
    <div>
      <Link
        href="/console/messages"
        className="mb-4 inline-flex items-center gap-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
      >
        <Icon name="arrow-left" size={16} />
        대화 기록
      </Link>
      <BookTimeline bookId={bookId} />
    </div>
  );
}
