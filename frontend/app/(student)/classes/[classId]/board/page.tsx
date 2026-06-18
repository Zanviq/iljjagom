import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { getBoardPosts } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { BoardPostStatus, BoardPostSummary } from "@/lib/types";

const STATUS_META: Record<
  BoardPostStatus,
  { label: string; tone: "warning" | "success" | "danger" }
> = {
  pending: { label: "승인 대기", tone: "warning" },
  published: { label: "공개됨", tone: "success" },
  rejected: { label: "반려됨", tone: "danger" },
};

export default async function ClassBoardPage({
  params,
}: {
  params: Promise<{ classId: string }>;
}) {
  const { classId } = await params;
  const token = await getAccessToken();

  let posts: BoardPostSummary[] = [];
  try {
    posts = (await getBoardPosts(token, classId)).posts;
  } catch {
    // 게시판 미구현/빈 상태 — 빈 목록으로 graceful.
    posts = [];
  }

  return (
    <div className="mx-auto w-full max-w-[var(--width-content)] px-6 pb-24 pt-9">
      <Link
        href="/home"
        className="inline-flex items-center gap-1.5 py-1.5 text-[length:var(--text-sm)] font-bold text-ink-3"
      >
        <Icon name="arrow-left" size={16} />
        내 책장
      </Link>
      <h1
        className="mb-1 mt-2"
        style={{
          fontFamily: "var(--font-serif)",
          fontWeight: 600,
          fontSize: 36,
          letterSpacing: "-.02em",
          color: "var(--text-1)",
        }}
      >
        학급 게시판
      </h1>
      <p className="mb-7 text-[length:var(--text-md)] text-ink-2">
        친구들이 만든 이야기를 구경해 봐요.
      </p>

      {posts.length === 0 ? (
        <EmptyState icon="megaphone" title="아직 발표된 이야기가 없어요">
          이야기를 완성하고 학급에 발표하면 여기에 보여요.
        </EmptyState>
      ) : (
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(290px,1fr))]">
          {posts.map((p) => (
            <BoardCard key={p.id} classId={classId} post={p} />
          ))}
        </div>
      )}
    </div>
  );
}

function BoardCard({
  classId,
  post,
}: {
  classId: string;
  post: BoardPostSummary;
}) {
  const meta = STATUS_META[post.status];
  const s = post.snapshot;
  return (
    <Link href={`/classes/${classId}/board/${post.id}`} className="block">
      <Card interactive padding="lg" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="flex items-start justify-between gap-2.5">
          <span
            className="flex h-10 w-10 items-center justify-center rounded-[10px]"
            style={{ background: "var(--primary-tint)", color: "var(--primary-text)" }}
            aria-hidden
          >
            <Icon name="book-open" size={20} />
          </span>
          {meta && (
            <Badge tone={meta.tone} dot>
              {meta.label}
            </Badge>
          )}
        </div>
        <div>
          <h3
            className="truncate"
            style={{
              fontFamily: "var(--font-serif)",
              fontWeight: 600,
              fontSize: 20,
              color: "var(--text-1)",
            }}
          >
            {post.title || "제목 없는 이야기"}
          </h3>
          <p className="mt-0.5 text-[length:var(--text-sm)] text-ink-3">
            {post.studentName}
          </p>
        </div>
        <div className="flex flex-wrap gap-3 text-[length:var(--text-xs)] text-ink-3">
          {typeof s.chapterCount === "number" && (
            <span className="inline-flex items-center gap-1">
              <Icon name="layers" size={13} />
              {s.chapterCount}장
            </span>
          )}
          {typeof s.letterCount === "number" && s.letterCount > 0 && (
            <span className="inline-flex items-center gap-1">
              <Icon name="mail" size={13} />
              편지 {s.letterCount}
            </span>
          )}
          {s.emotionLogged && (
            <span className="inline-flex items-center gap-1">
              <Icon name="pen-line" size={13} />
              감정 곡선
            </span>
          )}
        </div>
      </Card>
    </Link>
  );
}
