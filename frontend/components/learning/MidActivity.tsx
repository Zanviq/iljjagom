"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { EssayForm } from "@/components/learning/EssayForm";
import { Quiz } from "@/components/learning/Quiz";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorText } from "@/components/ui/ErrorText";
import { Icon } from "@/components/ui/Icon";
import { Loading } from "@/components/ui/Loading";
import { ApiError, completeMidActivity, getMidActivity } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { MidActivity as MidActivityData } from "@/lib/types";

/**
 * 중간활동(04 기능개선 학생/15 §3). 기·승 협업이 끝나면 전·결 진입 전에
 * 중간 퀴즈/독후감을 푼다. 학생이 푸는 "동안" 백엔드가 전·결을 선생성하므로,
 * 완료 버튼을 누르면 게이트가 풀리고 곧바로(대기 없이) 읽기로 이어진다.
 *
 * graceful: 엔드포인트 미구현(404)이거나 required=false(이미 했거나 해당 없음)면
 * 읽기 화면으로 곧바로 보낸다(현 동작 보존).
 */
export function MidActivity({ bookId }: { bookId: string }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [data, setData] = useState<MidActivityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [finishing, setFinishing] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      const t = await getClientAccessToken();
      if (!active) return;
      setToken(t);
      try {
        const res = await getMidActivity(t, bookId);
        if (!active) return;
        // 노출 대상이 아니면(미구현 폴백 포함) 바로 읽기로.
        if (!res.required) {
          router.replace(`/books/${bookId}/read`);
          return;
        }
        setData(res);
      } catch (e) {
        if (!active) return;
        if (e instanceof ApiError && (e.status === 404 || e.status === 0)) {
          router.replace(`/books/${bookId}/read`);
          return;
        }
        setError(
          e instanceof ApiError ? e.message : "활동을 불러오지 못했어요.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [bookId, router]);

  async function finish() {
    if (finishing) return;
    setFinishing(true);
    setError(null);
    try {
      await completeMidActivity(token, bookId);
    } catch (e) {
      // 게이트 해제 실패해도 막지 않는다(읽기 진입 시 전·결이 아직이면 그쪽에서 재안내).
      if (e instanceof ApiError && e.status !== 404 && e.status !== 0) {
        setError(e.message);
        setFinishing(false);
        return;
      }
    }
    router.push(`/books/${bookId}/read`);
  }

  if (loading) {
    return <Loading card>중간활동을 준비하는 중이에요…</Loading>;
  }
  if (error && !data) {
    return <ErrorText>{error}</ErrorText>;
  }
  if (!data) return null;

  const hasContent = data.quiz.length > 0 || data.essayBlanks.length > 0;

  return (
    <div className="flex flex-col gap-9">
      <Card tone="accent" padding="lg" style={{ display: "flex", gap: 12 }}>
        <Icon
          name="sparkles"
          size={22}
          style={{ color: "var(--accent-text)", flex: "none", marginTop: 2 }}
        />
        <div>
          <p
            className="text-[length:var(--text-md)] font-bold"
            style={{ color: "var(--accent-text)" }}
          >
            여기까지 이야기를 함께 만들었어요!
          </p>
          <p className="mt-1 text-[length:var(--text-sm)] text-ink-2">
            잠깐 활동을 하는 동안 곰 작가가 이야기의 뒷부분을 준비할게요. 다
            끝내면 바로 이어서 읽을 수 있어요.
          </p>
        </div>
      </Card>

      {data.quiz.length > 0 && (
        <Block icon="circle-help" title="중간 퀴즈">
          <Quiz items={data.quiz} bookId={bookId} />
        </Block>
      )}

      {data.essayBlanks.length > 0 && (
        <Block icon="notebook-pen" title="중간 생각 나누기">
          <EssayForm bookId={bookId} blanks={data.essayBlanks} />
        </Block>
      )}

      {!hasContent && (
        <p className="text-[length:var(--text-md)] text-ink-2">
          준비된 활동이 없어요. 아래 버튼으로 이야기를 이어가요.
        </p>
      )}

      {error && <ErrorText>{error}</ErrorText>}

      <div className="flex flex-col items-center gap-2 border-t border-line pt-7">
        <Button
          size="lg"
          iconRight="arrow-right"
          onClick={() => void finish()}
          loading={finishing}
        >
          {finishing ? "이야기를 준비하는 중…" : "이야기 마무리 지으러 가기"}
        </Button>
        <p className="text-[length:var(--text-sm)] text-ink-3">
          전·결(이야기의 뒷부분)로 이어집니다.
        </p>
      </div>
    </div>
  );
}

function Block({
  icon,
  title,
  children,
}: {
  icon: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-3.5 flex items-center gap-2.5">
        <span
          className="flex h-[34px] w-[34px] items-center justify-center rounded-[10px]"
          style={{ background: "var(--accent-tint)", color: "var(--accent-text)" }}
          aria-hidden
        >
          <Icon name={icon} size={18} />
        </span>
        <h2 className="text-[length:var(--text-lg)] font-extrabold text-ink">
          {title}
        </h2>
      </div>
      {children}
    </section>
  );
}
