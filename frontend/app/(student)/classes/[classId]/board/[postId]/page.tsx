import Link from "next/link";
import { notFound } from "next/navigation";

import { BoardCover } from "@/components/board/BoardCover";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { ApiError, getBoardPost } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { BoardPostStatus } from "@/lib/types";

const STATUS_META: Record<
  BoardPostStatus,
  { label: string; tone: "warning" | "success" | "danger" }
> = {
  pending: { label: "승인 대기", tone: "warning" },
  published: { label: "공개됨", tone: "success" },
  rejected: { label: "반려됨", tone: "danger" },
};

export default async function BoardPostDetailPage({
  params,
}: {
  params: Promise<{ classId: string; postId: string }>;
}) {
  const { classId, postId } = await params;
  const token = await getAccessToken();

  let post;
  try {
    post = await getBoardPost(token, postId);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 0)) notFound();
    throw e;
  }

  const meta = STATUS_META[post.status];
  const s = post.snapshot;

  return (
    <div className="mx-auto w-full max-w-[740px] px-6 pb-20 pt-6">
      <Link
        href={`/classes/${classId}/board`}
        className="inline-flex items-center gap-1.5 py-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
      >
        <Icon name="arrow-left" size={16} />
        학급 게시판
      </Link>

      <div className="mb-5 mt-2 flex items-center justify-between gap-3">
        <h1
          style={{
            fontFamily: "var(--font-serif)",
            fontWeight: 600,
            fontSize: 34,
            letterSpacing: "-.02em",
            color: "var(--text-1)",
          }}
        >
          {post.title || "제목 없는 이야기"}
        </h1>
        {meta && (
          <Badge tone={meta.tone} dot>
            {meta.label}
          </Badge>
        )}
      </div>

      {s.coverIllustration && (
        <div className="mb-6">
          <BoardCover url={s.coverIllustration} alt={post.title || "이야기 표지"} height={260} />
        </div>
      )}

      {post.intro && (
        <Card padding="lg" className="mb-6">
          <p className="whitespace-pre-wrap text-[length:var(--text-md)] text-ink-1">
            {post.intro}
          </p>
        </Card>
      )}

      <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(150px,1fr))]">
        {typeof s.chapterCount === "number" && (
          <SnapStat icon="layers" label="장 수" value={`${s.chapterCount}장`} />
        )}
        {typeof s.letterCount === "number" && (
          <SnapStat icon="mail" label="편지" value={`${s.letterCount}통`} />
        )}
        {typeof s.quizScore === "number" && (
          <SnapStat icon="circle-help" label="퀴즈" value={`${s.quizScore}점`} />
        )}
        {s.emotionLogged && (
          <SnapStat icon="pen-line" label="감정 곡선" value="기록함" />
        )}
      </div>

      {post.status === "rejected" && post.reviewNote && (
        <Card padding="lg" tone="accent" className="mt-6">
          <p className="text-[length:var(--text-sm)] font-bold" style={{ color: "var(--accent-text)" }}>
            선생님 메모: {post.reviewNote}
          </p>
        </Card>
      )}
    </div>
  );
}

function SnapStat({
  icon,
  label,
  value,
}: {
  icon: string;
  label: string;
  value: string;
}) {
  return (
    <Card padding="md">
      <div className="flex items-center gap-1.5 text-[length:var(--text-xs)] text-ink-3">
        <Icon name={icon} size={14} />
        {label}
      </div>
      <p className="mt-1 text-[length:var(--text-lg)] font-extrabold text-ink">
        {value}
      </p>
    </Card>
  );
}
