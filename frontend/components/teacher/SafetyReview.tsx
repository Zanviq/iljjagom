"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { SeverityBadge } from "@/components/admin/SafetyFlagList";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Checkbox } from "@/components/ui/Checkbox";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
import { Textarea } from "@/components/ui/Textarea";
import {
  approveLetter,
  ApiError,
  rejectLetter,
  resolveSafetyFlag,
} from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { Letter, SafetyFlag } from "@/lib/types";

/**
 * 교사 안전 검토(03): 보류된 편지(승인/미발송) + 미처리 안전 신호(종결).
 * 액션 성공 시 router.refresh()로 서버 데이터 갱신.
 */
export function SafetyReview({
  letters,
  flags,
}: {
  letters: Letter[];
  flags: SafetyFlag[];
}) {
  return (
    <div className="flex flex-col gap-9">
      <section>
        <h2 className="mb-3 text-[length:var(--text-md)] font-extrabold text-ink">
          보류된 편지 ({letters.length})
        </h2>
        {letters.length === 0 ? (
          <EmptyState icon="mail-check" title="검토할 편지가 없어요" />
        ) : (
          <div className="flex flex-col gap-3">
            {letters.map((l) => (
              <LetterCard key={l.id} letter={l} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-[length:var(--text-md)] font-extrabold text-ink">
          미처리 안전 신호 ({flags.length})
        </h2>
        {flags.length === 0 ? (
          <EmptyState icon="shield-check" title="미처리 신호가 없어요" />
        ) : (
          <div className="flex flex-col gap-3">
            {flags.map((f) => (
              <FlagCard key={f.id} flag={f} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function LetterCard({ letter }: { letter: Letter }) {
  const router = useRouter();
  const [mode, setMode] = useState<"none" | "approve" | "reject">("none");
  const [reply, setReply] = useState("");
  const [useAi, setUseAi] = useState(true);
  const [note, setNote] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
    setPending(true);
    setError(null);
    try {
      await fn();
      router.refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "처리하지 못했어요.");
      setPending(false);
    }
  }

  return (
    <Card padding="lg">
      <p className="text-[length:var(--text-sm)] font-bold text-ink-3">
        받는 인물: {letter.recipient}
      </p>
      <p className="mt-1 whitespace-pre-wrap text-ink">{letter.body}</p>

      {mode === "none" && (
        <div className="mt-3 flex gap-2">
          <Button onClick={() => setMode("approve")}>답장 승인</Button>
          <Button variant="outline" onClick={() => setMode("reject")}>
            미발송
          </Button>
        </div>
      )}

      {mode === "approve" && (
        <div className="mt-3">
          <Checkbox
            label="AI 페르소나 답장 생성"
            checked={useAi}
            onChange={(e) => setUseAi(e.target.checked)}
          />
          {!useAi && (
            <Textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              rows={3}
              placeholder="직접 답장을 적어요"
              className="mt-2"
            />
          )}
          {error && <ErrorText className="mt-2">{error}</ErrorText>}
          <div className="mt-3 flex gap-2">
            <Button
              disabled={pending || (!useAi && !reply.trim())}
              loading={pending}
              className="flex-1"
              onClick={() =>
                void run(async () => {
                  const token = await getClientAccessToken();
                  await approveLetter(token, letter.id, {
                    useAiReply: useAi,
                    reply: useAi ? undefined : reply.trim(),
                  });
                })
              }
            >
              {pending ? "처리 중…" : "승인하고 보내기"}
            </Button>
            <Button variant="ghost" onClick={() => setMode("none")}>
              취소
            </Button>
          </div>
        </div>
      )}

      {mode === "reject" && (
        <div className="mt-3">
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="메모(선택)"
          />
          {error && <ErrorText className="mt-2">{error}</ErrorText>}
          <div className="mt-3 flex gap-2">
            <Button
              variant="danger"
              disabled={pending}
              loading={pending}
              className="flex-1"
              onClick={() =>
                void run(async () => {
                  const token = await getClientAccessToken();
                  await rejectLetter(token, letter.id, note.trim() || undefined);
                })
              }
            >
              {pending ? "처리 중…" : "미발송 처리"}
            </Button>
            <Button variant="ghost" onClick={() => setMode("none")}>
              취소
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

function FlagCard({ flag }: { flag: SafetyFlag }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function resolve() {
    setPending(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      await resolveSafetyFlag(token, flag.id, note.trim() || undefined);
      router.refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "처리하지 못했어요.");
      setPending(false);
    }
  }

  return (
    <Card padding="lg" accentEdge="warning">
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={flag.severity} />
        <Badge tone="neutral">{flag.source}</Badge>
      </div>
      <p className="mt-2 text-[length:var(--text-sm)] text-ink">{flag.reason}</p>

      {open ? (
        <div className="mt-3">
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="종결 메모(선택)"
          />
          {error && <ErrorText className="mt-2">{error}</ErrorText>}
          <div className="mt-3 flex gap-2">
            <Button
              disabled={pending}
              loading={pending}
              className="flex-1"
              onClick={() => void resolve()}
            >
              {pending ? "처리 중…" : "종결하기"}
            </Button>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              취소
            </Button>
          </div>
        </div>
      ) : (
        <Button variant="outline" icon="check" className="mt-3" onClick={() => setOpen(true)}>
          종결 처리
        </Button>
      )}
    </Card>
  );
}
