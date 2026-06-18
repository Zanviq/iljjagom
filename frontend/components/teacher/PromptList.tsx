"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { ApiError, closePrompt } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { AssessmentType, Prompt } from "@/lib/types";

const ASSESSMENT_LABEL: Record<AssessmentType, string> = {
  quiz: "퀴즈",
  essay: "독후감",
  none: "평가 없음",
};
const LANGUAGE_LABEL: Record<string, string> = { ko: "한국어", en: "English" };

/**
 * 낸 발제 목록(04 기능개선 교사/02 B). 상태 배지 + 마감(신규 책 차단).
 * 발제별 학생 작성 드릴다운은 T5(submissions)에서 연결.
 */
export function PromptList({
  classId,
  initial,
}: {
  classId: string;
  initial: Prompt[];
}) {
  const [prompts, setPrompts] = useState<Prompt[]>(initial);

  function onClosed(updated: Prompt) {
    setPrompts((ps) => ps.map((p) => (p.id === updated.id ? updated : p)));
  }

  if (prompts.length === 0) {
    return (
      <p className="text-[length:var(--text-sm)] text-ink-3">
        아직 낸 발제가 없어요.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {prompts.map((p) => (
        <PromptCard key={p.id} classId={classId} prompt={p} onClosed={onClosed} />
      ))}
    </div>
  );
}

function PromptCard({
  classId,
  prompt,
  onClosed,
}: {
  classId: string;
  prompt: Prompt;
  onClosed: (p: Prompt) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const closed = prompt.status === "closed";

  async function close() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      const updated = await closePrompt(token, classId, prompt.id);
      onClosed(updated);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.status === 404 || e.status === 0
            ? "발제 마감을 준비하고 있어요."
            : e.message
          : "발제를 마감하지 못했어요.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card padding="md">
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-[length:var(--text-base)] font-extrabold text-ink">
          {prompt.topic}
        </h4>
        <Badge tone={closed ? "neutral" : "success"} dot>
          {closed ? "마감됨" : "진행 중"}
        </Badge>
      </div>

      {prompt.learningObjectives.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {prompt.learningObjectives.map((o, i) => (
            <Chip key={i}>{o}</Chip>
          ))}
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        <Badge tone="primary" icon="clipboard-check">
          {ASSESSMENT_LABEL[prompt.assessment.type]}
        </Badge>
        <Badge tone="info" icon="languages">
          {LANGUAGE_LABEL[prompt.language] ?? prompt.language}
        </Badge>
        {typeof prompt.gradeBand === "number" && (
          <Badge tone="neutral" icon="graduation-cap">
            {prompt.gradeBand}학년
          </Badge>
        )}
        {typeof prompt.chaptersPlanned === "number" && (
          <Badge tone="neutral" icon="layers">
            {prompt.chaptersPlanned}장
          </Badge>
        )}
        {prompt.dueAt && (
          <Badge tone="warning" icon="calendar-clock">
            마감 {new Date(prompt.dueAt).toLocaleDateString("ko-KR")}
          </Badge>
        )}
      </div>

      {error && (
        <p className="mt-2 text-[length:var(--text-sm)] font-bold" style={{ color: "var(--danger-text)" }}>
          {error}
        </p>
      )}

      {!closed && (
        <div className="mt-3">
          <Button
            size="sm"
            variant="outline"
            icon="lock"
            onClick={() => void close()}
            loading={busy}
          >
            발제 마감
          </Button>
        </div>
      )}
    </Card>
  );
}
