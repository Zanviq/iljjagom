"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { SeverityBadge } from "@/components/admin/SafetyFlagList";
import { buttonClass } from "@/components/ui/Button";
import { ErrorText } from "@/components/ui/ErrorText";
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
    <div className="space-y-10">
      <section>
        <h2 className="mb-3 text-lg font-bold">
          보류된 편지 ({letters.length})
        </h2>
        {letters.length === 0 ? (
          <p className="rounded-card bg-surface p-5 text-muted ring-1 ring-border">
            검토할 편지가 없어요. 👍
          </p>
        ) : (
          <ul className="space-y-3">
            {letters.map((l) => (
              <LetterCard key={l.id} letter={l} />
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-bold">
          미처리 안전 신호 ({flags.length})
        </h2>
        {flags.length === 0 ? (
          <p className="rounded-card bg-surface p-5 text-muted ring-1 ring-border">
            미처리 신호가 없어요. 👍
          </p>
        ) : (
          <ul className="space-y-3">
            {flags.map((f) => (
              <FlagCard key={f.id} flag={f} />
            ))}
          </ul>
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
    <li className="rounded-card bg-surface p-4 ring-1 ring-border">
      <p className="text-sm font-bold text-muted">받는 인물: {letter.recipient}</p>
      <p className="mt-1 whitespace-pre-wrap">{letter.body}</p>

      {mode === "none" && (
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => setMode("approve")}
            className={buttonClass("primary", "md")}
          >
            답장 승인
          </button>
          <button
            onClick={() => setMode("reject")}
            className={buttonClass("outline", "md")}
          >
            미발송
          </button>
        </div>
      )}

      {mode === "approve" && (
        <div className="mt-3">
          <label className="flex items-center gap-2 text-sm font-bold">
            <input
              type="checkbox"
              checked={useAi}
              onChange={(e) => setUseAi(e.target.checked)}
              className="h-5 w-5 accent-[var(--primary)]"
            />
            AI 페르소나 답장 생성
          </label>
          {!useAi && (
            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              rows={3}
              placeholder="직접 답장을 적어요"
              className="mt-2 w-full resize-none rounded-xl border-2 border-border bg-background p-3 text-lg"
            />
          )}
          {error && <ErrorText className="mt-2">{error}</ErrorText>}
          <div className="mt-3 flex gap-2">
            <button
              disabled={pending || (!useAi && !reply.trim())}
              onClick={() =>
                void run(async () => {
                  const token = await getClientAccessToken();
                  await approveLetter(token, letter.id, {
                    useAiReply: useAi,
                    reply: useAi ? undefined : reply.trim(),
                  });
                })
              }
              className={buttonClass("primary", "md", "flex-1")}
            >
              {pending ? "처리 중…" : "승인하고 보내기"}
            </button>
            <button
              onClick={() => setMode("none")}
              className={buttonClass("ghost", "md")}
            >
              취소
            </button>
          </div>
        </div>
      )}

      {mode === "reject" && (
        <div className="mt-3">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="메모(선택)"
            className="w-full resize-none rounded-xl border-2 border-border bg-background p-3 text-lg"
          />
          {error && <ErrorText className="mt-2">{error}</ErrorText>}
          <div className="mt-3 flex gap-2">
            <button
              disabled={pending}
              onClick={() =>
                void run(async () => {
                  const token = await getClientAccessToken();
                  await rejectLetter(token, letter.id, note.trim() || undefined);
                })
              }
              className={buttonClass("danger", "md", "flex-1")}
            >
              {pending ? "처리 중…" : "미발송 처리"}
            </button>
            <button
              onClick={() => setMode("none")}
              className={buttonClass("ghost", "md")}
            >
              취소
            </button>
          </div>
        </div>
      )}
    </li>
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
    <li className="rounded-card bg-surface p-4 ring-1 ring-border">
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={flag.severity} />
        <span className="rounded-full bg-black/5 px-2.5 py-0.5 text-xs font-bold text-muted">
          {flag.source}
        </span>
      </div>
      <p className="mt-2 text-sm">{flag.reason}</p>

      {open ? (
        <div className="mt-3">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="종결 메모(선택)"
            className="w-full resize-none rounded-xl border-2 border-border bg-background p-3 text-lg"
          />
          {error && <ErrorText className="mt-2">{error}</ErrorText>}
          <div className="mt-3 flex gap-2">
            <button
              disabled={pending}
              onClick={() => void resolve()}
              className={buttonClass("primary", "md", "flex-1")}
            >
              {pending ? "처리 중…" : "종결하기"}
            </button>
            <button
              onClick={() => setOpen(false)}
              className={buttonClass("ghost", "md")}
            >
              취소
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className={buttonClass("outline", "md", "mt-3")}
        >
          종결 처리
        </button>
      )}
    </li>
  );
}
