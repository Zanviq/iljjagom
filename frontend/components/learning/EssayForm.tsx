"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorText } from "@/components/ui/ErrorText";
import { Textarea } from "@/components/ui/Textarea";
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
      <div className="flex flex-col gap-4">
        {blanks.map((b, i) => (
          <Card key={i} padding="lg">
            <p className="font-bold text-ink">{b.prompt}</p>
            {b.hints.length > 0 && (
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {b.hints.map((h, hi) => (
                  <li
                    key={hi}
                    className="rounded-full bg-accent-tint px-2.5 py-0.5 text-[length:var(--text-sm)] text-accent-text"
                  >
                    {h}
                  </li>
                ))}
              </ul>
            )}
            <Textarea
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
              className="mt-3"
            />
          </Card>
        ))}
      </div>
      {error && <ErrorText className="mt-3">{error}</ErrorText>}
      <div className="mt-3 flex items-center gap-3">
        <Button onClick={() => void save()} disabled={!canSave} loading={saving}>
          {saving ? "저장 중…" : "독후감 저장"}
        </Button>
        {saved && (
          <span
            role="status"
            className="text-[length:var(--text-sm)] font-bold"
            style={{ color: "var(--success-text)" }}
          >
            저장했어요!
          </span>
        )}
      </div>
    </div>
  );
}
