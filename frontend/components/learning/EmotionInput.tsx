"use client";

import { useState } from "react";

import { EmotionCurve } from "@/components/learning/EmotionCurve";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorText } from "@/components/ui/ErrorText";
import { ApiError, postLearningResult } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { EmotionFrame } from "@/lib/types";

interface Row {
  chapterIdx: number;
  label: string | null;
  value: number;
}

/**
 * 감정 곡선 학생 입력(04 기능개선 11). 장별로 감정(라벨)·세기(0~1)를 고르면
 * 곡선이 그려지고 저장한다. 저장은 POST learning-results(type=emotion).
 */
export function EmotionInput({
  bookId,
  frame,
}: {
  bookId: string;
  frame: EmotionFrame;
}) {
  const [rows, setRows] = useState<Row[]>(() =>
    frame.points.map((p) => ({
      chapterIdx: p.chapterIdx,
      label: p.label,
      value: p.value ?? 0.5,
    })),
  );
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function setLabel(i: number, label: string) {
    setSaved(false);
    setRows((prev) =>
      prev.map((r, idx) =>
        idx === i ? { ...r, label: r.label === label ? null : label } : r,
      ),
    );
  }
  function setValue(i: number, value: number) {
    setSaved(false);
    setRows((prev) =>
      prev.map((r, idx) => (idx === i ? { ...r, value } : r)),
    );
  }

  const hasAny = rows.some((r) => r.label !== null);

  async function save() {
    if (!hasAny || saving) return;
    setSaving(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      await postLearningResult(token, bookId, {
        type: "emotion",
        data: {
          points: rows.map((r) => ({
            chapterIdx: r.chapterIdx,
            label: r.label,
            value: r.value,
          })),
        },
      });
      setSaved(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "감정 곡선을 저장하지 못했어요.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-[length:var(--text-sm)] text-ink-3">
        각 장면에서 어떤 마음이었는지 골라 보고, 그 마음이 얼마나 컸는지 막대를
        움직여 봐요.
      </p>

      <EmotionCurve
        points={rows.map((r) => ({
          chapterIdx: r.chapterIdx,
          label: r.label,
          value: r.value,
        }))}
      />

      <div className="flex flex-col gap-3">
        {rows.map((r, i) => (
          <Card key={r.chapterIdx} padding="md">
            <div className="mb-2.5 flex items-center justify-between">
              <span className="text-[length:var(--text-sm)] font-extrabold text-ink">
                {r.chapterIdx}장
              </span>
              <input
                type="range"
                min={0}
                max={100}
                value={Math.round(r.value * 100)}
                onChange={(e) => setValue(i, Number(e.target.value) / 100)}
                aria-label={`${r.chapterIdx}장 감정 세기`}
                className="w-[55%]"
                style={{ accentColor: "var(--accent)" }}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              {frame.labels.map((label) => {
                const selected = r.label === label;
                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => setLabel(i, label)}
                    aria-pressed={selected}
                    style={{
                      height: 34,
                      padding: "0 13px",
                      borderRadius: 999,
                      fontWeight: 700,
                      fontSize: "var(--text-sm)",
                      cursor: "pointer",
                      background: selected
                        ? "var(--accent)"
                        : "var(--surface-2)",
                      color: selected
                        ? "var(--on-accent)"
                        : "var(--text-2)",
                      border: selected
                        ? "var(--border) solid transparent"
                        : "var(--border) solid var(--line)",
                    }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </Card>
        ))}
      </div>

      {error && <ErrorText>{error}</ErrorText>}

      <div className="flex items-center gap-3">
        <Button
          icon="save"
          onClick={() => void save()}
          disabled={!hasAny || saving}
          loading={saving}
          style={{ alignSelf: "flex-start" }}
        >
          {saving ? "저장하는 중…" : "감정 곡선 저장"}
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
