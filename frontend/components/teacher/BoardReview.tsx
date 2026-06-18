"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  ApiError,
  approveBoardPost,
  getBoardPosts,
  rejectBoardPost,
} from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { BoardPostStatus, BoardPostSummary } from "@/lib/types";

const STATUS_META: Record<
  BoardPostStatus,
  { label: string; tone: "warning" | "success" | "danger" }
> = {
  pending: { label: "승인 대기", tone: "warning" },
  published: { label: "공개됨", tone: "success" },
  rejected: { label: "반려됨", tone: "danger" },
};

/** 학급 발표 승인 큐(04 기능개선 학생/15·14 교사 측). 미구현 시 graceful. */
export function BoardReview({ classId }: { classId: string }) {
  const [posts, setPosts] = useState<BoardPostSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const token = await getClientAccessToken();
        if (!active) return;
        setLoading(true);
        const { posts: ps } = await getBoardPosts(token, classId);
        if (active) setPosts(ps);
      } catch {
        if (active) setUnavailable(true);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [classId]);

  function onStatus(id: string, status: BoardPostStatus) {
    setPosts((ps) => ps.map((p) => (p.id === id ? { ...p, status } : p)));
  }

  if (loading) {
    return <p className="text-[length:var(--text-sm)] text-ink-3">불러오는 중이에요…</p>;
  }
  if (unavailable) {
    return (
      <EmptyState icon="megaphone" title="게시판을 준비하고 있어요">
        잠시 후 다시 확인해 주세요.
      </EmptyState>
    );
  }
  if (posts.length === 0) {
    return (
      <EmptyState icon="megaphone" title="발표가 없어요">
        학생이 이야기를 발표하면 여기에서 승인할 수 있어요.
      </EmptyState>
    );
  }

  const pending = posts.filter((p) => p.status === "pending");
  const others = posts.filter((p) => p.status !== "pending");

  return (
    <div className="flex flex-col gap-6">
      <section>
        <h2 className="mb-3 text-[length:var(--text-md)] font-extrabold text-ink">
          승인 대기 ({pending.length})
        </h2>
        {pending.length === 0 ? (
          <p className="text-[length:var(--text-sm)] text-ink-3">
            대기 중인 발표가 없어요.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {pending.map((p) => (
              <ReviewCard key={p.id} post={p} onStatus={onStatus} />
            ))}
          </div>
        )}
      </section>

      {others.length > 0 && (
        <section>
          <h2 className="mb-3 text-[length:var(--text-md)] font-extrabold text-ink">
            처리됨
          </h2>
          <div className="flex flex-col gap-3">
            {others.map((p) => (
              <ReviewCard key={p.id} post={p} onStatus={onStatus} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ReviewCard({
  post,
  onStatus,
}: {
  post: BoardPostSummary;
  onStatus: (id: string, status: BoardPostStatus) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const meta = STATUS_META[post.status];

  async function act(kind: "approve" | "reject") {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      if (kind === "approve") {
        await approveBoardPost(token, post.id);
        onStatus(post.id, "published");
      } else {
        await rejectBoardPost(token, post.id);
        onStatus(post.id, "rejected");
      }
    } catch (e) {
      setError(
        e instanceof ApiError && (e.status === 404 || e.status === 0)
          ? "승인 기능을 준비하고 있어요."
          : "처리하지 못했어요.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3
            style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 19, color: "var(--text-1)" }}
          >
            {post.title || "제목 없는 이야기"}
          </h3>
          <p className="mt-0.5 text-[length:var(--text-sm)] text-ink-3">
            {post.studentName}
          </p>
        </div>
        {meta && (
          <Badge tone={meta.tone} dot>
            {meta.label}
          </Badge>
        )}
      </div>

      {error && (
        <p className="text-[length:var(--text-sm)] font-bold" style={{ color: "var(--danger-text)" }}>
          {error}
        </p>
      )}

      {post.status === "pending" && (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" icon="check" onClick={() => void act("approve")} loading={busy}>
            승인
          </Button>
          <Button size="sm" variant="outline" icon="x" onClick={() => void act("reject")} disabled={busy}>
            반려
          </Button>
        </div>
      )}
    </Card>
  );
}
