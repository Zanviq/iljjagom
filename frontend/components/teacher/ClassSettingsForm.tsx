"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Switch } from "@/components/ui/Switch";
import { ApiError, putClassSettings } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type {
  ClassSettingsResponse,
  CoachingLevel,
  SafetyLevel,
} from "@/lib/types";

const SAFETY_OPTIONS: { value: SafetyLevel; label: string; hint: string }[] = [
  { value: "relaxed", label: "느슨", hint: "표현을 폭넓게 허용" },
  { value: "standard", label: "표준", hint: "권장 기본값" },
  { value: "strict", label: "엄격", hint: "민감한 표현을 강하게 차단" },
];

// 자유집필에서 곰작가가 학생 글에 끼어드는 정도(06 §5).
const COACHING_OPTIONS: { value: CoachingLevel; label: string; hint: string }[] = [
  { value: "off", label: "끄기", hint: "끼어들지 않고 그대로 써요" },
  { value: "light", label: "약하게", hint: "흐름이 끊길 때만 살짝 (권장)" },
  { value: "standard", label: "표준", hint: "흐름·학습 주제까지 챙겨요" },
];

/** featureToggles 키 → 한국어 라벨(미등록 키는 키 그대로 표시). */
const TOGGLE_LABELS: Record<string, string> = {
  boardAutoPublish: "게시판 자동 공개",
  board: "학급 게시판",
  intermediateActivities: "중간 학습활동(필수)",
  letterCharacterChoice: "편지 인물 선택",
  emotionCurveInput: "감정 곡선 학생 입력",
};

/**
 * 학급 설정 컨트롤러(04 기능개선 교사/02 C). 안전강도 + 기능 토글.
 * 미구현 PUT(404)은 안내(graceful).
 */
export function ClassSettingsForm({
  classId,
  initial,
}: {
  classId: string;
  initial: ClassSettingsResponse;
}) {
  const eff = initial.value;
  const [safetyLevel, setSafetyLevel] = useState<SafetyLevel>(
    eff.safetyLevel ?? initial.defaults.safetyLevel ?? "standard",
  );
  const [coachingLevel, setCoachingLevel] = useState<CoachingLevel>(
    eff.coachingLevel ?? initial.defaults.coachingLevel ?? "light",
  );
  // 기본값 키 + 현재값 키 합집합으로 토글 목록 구성.
  const toggleKeys = Array.from(
    new Set([
      ...Object.keys(initial.defaults.featureToggles ?? {}),
      ...Object.keys(eff.featureToggles ?? {}),
    ]),
  );
  const [toggles, setToggles] = useState<Record<string, boolean>>(() => {
    const merged: Record<string, boolean> = {
      ...(initial.defaults.featureToggles ?? {}),
      ...(eff.featureToggles ?? {}),
    };
    return merged;
  });

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (saving) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const token = await getClientAccessToken();
      await putClassSettings(token, classId, {
        safetyLevel,
        coachingLevel,
        featureToggles: toggles,
      });
      setSaved(true);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.status === 404 || e.status === 0
            ? "설정 저장을 준비하고 있어요. 조금만 기다려 주세요."
            : e.message
          : "설정을 저장하지 못했어요.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex max-w-[640px] flex-col gap-6">
      <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <h2 className="text-[length:var(--text-md)] font-extrabold text-ink">
            안전 강도
          </h2>
          <p className="mt-0.5 text-[length:var(--text-sm)] text-ink-2">
            AI가 만드는 이야기의 표현 수위를 학급에 맞게 정해요.
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          {SAFETY_OPTIONS.map((o) => {
            const selected = safetyLevel === o.value;
            return (
              <button
                key={o.value}
                type="button"
                onClick={() => {
                  setSafetyLevel(o.value);
                  setSaved(false);
                }}
                aria-pressed={selected}
                className="flex flex-col items-start gap-0.5 rounded-[var(--radius-control)] px-4 py-2.5"
                style={{
                  minWidth: 130,
                  cursor: "pointer",
                  background: selected ? "var(--primary)" : "var(--surface-2)",
                  color: selected ? "var(--on-primary)" : "var(--text-2)",
                  border: selected
                    ? "var(--border) solid transparent"
                    : "var(--border) solid var(--line)",
                }}
              >
                <span className="font-extrabold">{o.label}</span>
                <span
                  className="text-[length:var(--text-xs)]"
                  style={{ color: selected ? "var(--on-primary)" : "var(--text-3)" }}
                >
                  {o.hint}
                </span>
              </button>
            );
          })}
        </div>
      </Card>

      <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <h2 className="text-[length:var(--text-md)] font-extrabold text-ink">
            AI 지도 강도
          </h2>
          <p className="mt-0.5 text-[length:var(--text-sm)] text-ink-2">
            자유집필에서 곰작가가 학생 글에 끼어드는 정도를 정해요.
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          {COACHING_OPTIONS.map((o) => {
            const selected = coachingLevel === o.value;
            return (
              <button
                key={o.value}
                type="button"
                onClick={() => {
                  setCoachingLevel(o.value);
                  setSaved(false);
                }}
                aria-pressed={selected}
                className="flex flex-col items-start gap-0.5 rounded-[var(--radius-control)] px-4 py-2.5"
                style={{
                  minWidth: 150,
                  cursor: "pointer",
                  background: selected ? "var(--primary)" : "var(--surface-2)",
                  color: selected ? "var(--on-primary)" : "var(--text-2)",
                  border: selected
                    ? "var(--border) solid transparent"
                    : "var(--border) solid var(--line)",
                }}
              >
                <span className="font-extrabold">{o.label}</span>
                <span
                  className="text-[length:var(--text-xs)]"
                  style={{ color: selected ? "var(--on-primary)" : "var(--text-3)" }}
                >
                  {o.hint}
                </span>
              </button>
            );
          })}
        </div>
      </Card>

      {toggleKeys.length > 0 && (
        <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <h2 className="text-[length:var(--text-md)] font-extrabold text-ink">
              기능 사용
            </h2>
            <p className="mt-0.5 text-[length:var(--text-sm)] text-ink-2">
              학급에서 켜고 끌 활동을 선택해요.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            {toggleKeys.map((key) => (
              <Switch
                key={key}
                label={TOGGLE_LABELS[key] ?? key}
                checked={!!toggles[key]}
                onChange={(e) => {
                  const on = e.target.checked;
                  setToggles((t) => ({ ...t, [key]: on }));
                  setSaved(false);
                }}
              />
            ))}
          </div>
        </Card>
      )}

      {error && (
        <p className="text-[length:var(--text-sm)] font-bold" style={{ color: "var(--danger-text)" }}>
          {error}
        </p>
      )}

      <div className="flex items-center gap-3">
        <Button icon="save" onClick={() => void save()} loading={saving} style={{ alignSelf: "flex-start" }}>
          설정 저장
        </Button>
        {saved && (
          <span role="status" className="text-[length:var(--text-sm)] font-bold" style={{ color: "var(--success-text)" }}>
            저장했어요!
          </span>
        )}
      </div>
    </div>
  );
}
