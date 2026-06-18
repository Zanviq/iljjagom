"use client";

import { useState } from "react";

import { buttonClass } from "@/components/ui/Button";
import { ErrorText } from "@/components/ui/ErrorText";
import { ApiError, postLearningResult } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { EssayBlank } from "@/lib/types";

/**
 * 독후감 채우기 + 저장(추가기능 04: learning-results type=essay).
 * 자유 텍스트라 서버에서 안전 게이트 통과(위험 시 safety_flag) — 프론트는 결과 메시지만.
 */
export function EssayForm({
  bookId,
  blanks,
}: {
  bookId: string;
  blanks: EssayBlank[];
}) {
  const [texts, setTexts] = useState<string[]>(() => blanks.map(() => ""));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSave = !saving && texts.some((t) => t.trim().length > 0);

  async function save() {
    setSaving(true);
    setError(null);
    const data = {
      blanks: blanks.map((b, i) => ({ prompt: b.prompt, text: texts[i].trim() })),
    };
    try {
      const token = await getClientAccessToken();
      await postLearningResult(token, bookId, { type: "essay", data });
      setSaved(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "저장하지 못했어요.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <ul className="space-y-4">
        {blanks.map((b, i) => (
          <li key={i} className="rounded-card bg-surface p-5 ring-1 ring-border">
            <p className="font-bold">{b.prompt}</p>
            {b.hints.length > 0 && (
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {b.hints.map((h, hi) => (
                  <li
                    key={hi}
                    className="rounded-full bg-secondary/15 px-2.5 py-0.5 text-sm text-secondary-strong"
                  >
                    {h}
                  </li>
                ))}
              </ul>
            )}
            <textarea
              value={texts[i]}
              onChange={(e) =>
                setTexts((prev) => {
                  const next = [...prev];
                  next[i] = e.target.value;
                  setSaved(false);
                  return next;
                })
              }
              rows={3}
              placeholder="여기에 생각을 적어 봐요."
              className="mt-3 w-full rounded-xl border-2 border-border bg-background p-3"
            />
          </li>
        ))}
      </ul>
      {error && <ErrorText className="mt-3">{error}</ErrorText>}
      <div className="mt-3 flex items-center gap-3">
        <button
          onClick={() => void save()}
          disabled={!canSave}
          className={buttonClass("primary", "md")}
        >
          {saving ? "저장 중…" : "독후감 저장"}
        </button>
        {saved && (
          <span role="status" className="text-sm font-bold text-success-strong">
            저장했어요! 🎉
          </span>
        )}
      </div>
    </div>
  );
}
