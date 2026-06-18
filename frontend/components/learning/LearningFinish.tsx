"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { ApiError, getLearningResults, postBoardPost } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { BoardPostStatus } from "@/lib/types";

interface Summary {
  quiz: number;
  essay: number;
  emotion: number;
}

/**
 * 학습 마무리(04 기능개선 14). 완료 요약 + 후속 액션(메인 복귀·학급 발표).
 * 발표는 책 완독(status="done") 시에만 활성. 게시판/승인 상세는 학생/15가 정본.
 */
export function LearningFinish({
  bookId,
  classId,
  canPublish,
}: {
  bookId: string;
  classId: string | null;
  canPublish: boolean;
}) {
  const router = useRouter();
  const [summary, setSummary] = useState<Summary>({
    quiz: 0,
    essay: 0,
    emotion: 0,
  });
  const [posting, setPosting] = useState(false);
  const [posted, setPosted] = useState<BoardPostStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const token = await getClientAccessToken();
        const { results } = await getLearningResults(token, bookId);
        if (!active) return;
        setSummary({
          quiz: results.filter((r) => r.type === "quiz").length,
          essay: results.filter((r) => r.type === "essay").length,
          emotion: results.filter((r) => r.type === "emotion").length,
        });
      } catch {
        // 요약 조회 실패는 마무리 흐름을 막지 않는다.
      }
    })();
    return () => {
      active = false;
    };
  }, [bookId]);

  async function publish() {
    if (!canPublish || posting) return;
    setPosting(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      const res = await postBoardPost(token, bookId);
      setPosted(res.status);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.status === 404
            ? "학급 게시판을 준비하고 있어요. 조금만 기다려 주세요."
            : e.message
          : "발표를 등록하지 못했어요.",
      );
    } finally {
      setPosting(false);
    }
  }

  const items: { icon: string; label: string; done: boolean }[] = [
    { icon: "circle-help", label: "퀴즈", done: summary.quiz > 0 },
    { icon: "notebook-pen", label: "독후감", done: summary.essay > 0 },
    { icon: "pen-line", label: "감정 곡선", done: summary.emotion > 0 },
  ];

  return (
    <Card padding="lg" tone="accent" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <h2 className="text-[length:var(--text-lg)] font-extrabold text-ink">
          학습을 마무리해요
        </h2>
        <p className="mt-1 text-[length:var(--text-sm)] text-ink-2">
          오늘 한 활동을 확인하고, 다음으로 가 봐요.
        </p>
      </div>

      <div className="flex flex-wrap gap-2.5">
        {items.map((it) => (
          <span
            key={it.label}
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[length:var(--text-sm)] font-bold"
            style={{
              background: it.done ? "var(--success-tint)" : "var(--surface-2)",
              color: it.done ? "var(--success-text)" : "var(--text-3)",
              border: "var(--border) solid var(--line)",
            }}
          >
            <Icon name={it.done ? "check" : it.icon} size={15} />
            {it.label}
          </span>
        ))}
      </div>

      {posted ? (
        <p
          role="status"
          className="rounded-[var(--radius-input)] bg-surface p-4 font-bold"
          style={{ color: "var(--success-text)" }}
        >
          {posted === "published"
            ? "학급 게시판에 발표했어요!"
            : "발표를 등록했어요. 선생님이 확인한 뒤 학급에 공개돼요."}
        </p>
      ) : (
        <>
          {error && (
            <p
              className="text-[length:var(--text-sm)] font-bold"
              style={{ color: "var(--danger-text)" }}
            >
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Button icon="house" onClick={() => router.push("/home")}>
              메인으로 돌아가기
            </Button>
            <Button
              variant="accent"
              icon="megaphone"
              onClick={() => void publish()}
              disabled={!canPublish || posting}
              loading={posting}
              title={canPublish ? undefined : "이야기를 끝까지 읽으면 발표할 수 있어요."}
            >
              학급에 발표하기
            </Button>
          </div>
          {!canPublish && (
            <p className="text-[length:var(--text-xs)] text-ink-3">
              이야기를 끝까지 읽으면 학급에 발표할 수 있어요.
            </p>
          )}
        </>
      )}

      {posted && classId && (
        <Button
          variant="outline"
          iconRight="arrow-right"
          onClick={() => router.push(`/classes/${classId}/board`)}
          style={{ alignSelf: "flex-start" }}
        >
          학급 게시판 보러가기
        </Button>
      )}
    </Card>
  );
}
