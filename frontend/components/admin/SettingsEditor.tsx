"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorText } from "@/components/ui/ErrorText";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { Textarea } from "@/components/ui/Textarea";
import { ApiError, putAdminSettings } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";

/**
 * 런타임 설정 편집(추가기능 06 + 04 기능개선 관리자/02). 알려진 키는 선택형
 * 컨트롤(드롭다운/토글/스텝퍼), 그 외는 JSON 폴백. 저장은 PUT /admin/settings.
 * 시크릿은 settings 에 없음(env 존재여부만 별도 표시).
 */

const TEXT_MODELS = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"];
const EMBED_MODELS = ["gemini-embedding-001"];
const IMAGEN_MODELS = ["imagen-4.0-generate-001"];
const MODEL_FIELDS: { key: string; label: string; opts: string[] }[] = [
  { key: "designer", label: "설계 AI", opts: TEXT_MODELS },
  { key: "writer", label: "집필 AI", opts: TEXT_MODELS },
  { key: "editor", label: "편집 AI", opts: TEXT_MODELS },
  { key: "chat", label: "대화 AI", opts: TEXT_MODELS },
  { key: "embed", label: "임베딩", opts: EMBED_MODELS },
  { key: "imagen", label: "삽화 생성", opts: IMAGEN_MODELS },
];
const TOGGLE_FIELDS: { key: string; label: string }[] = [
  { key: "guided_mode", label: "유도(가이드) 모드" },
  { key: "illustrations", label: "삽화 생성" },
  { key: "letters", label: "편지 기능" },
];
const RATE_BUCKETS: { key: string; label: string }[] = [
  { key: "plan", label: "기획" },
  { key: "design", label: "설계" },
  { key: "revise", label: "수정" },
  { key: "letters", label: "편지" },
  { key: "learning", label: "학습" },
];
const WINDOW_OPTS = [30, 60, 120, 300];
const NOTIFY_OPTS = [60, 120, 180, 300, 600];
const SAFETY_OPTS = [
  { value: "relaxed", label: "완화" },
  { value: "standard", label: "표준" },
  { value: "strict", label: "엄격" },
];

const KNOWN = new Set([
  "models",
  "feature_toggles",
  "rate_limits",
  "notify_interval_sec",
  "safety_level",
]);

export function SettingsEditor({
  settings,
}: {
  settings: Record<string, unknown>;
}) {
  const keys = Object.keys(settings);
  if (keys.length === 0) {
    return <p className="text-ink-2">편집 가능한 설정이 없어요.</p>;
  }
  return (
    <div className="flex flex-col gap-4">
      {keys.map((k) => {
        const v = settings[k];
        if (k === "models") return <ModelsCard key={k} value={obj(v)} />;
        if (k === "feature_toggles") return <TogglesCard key={k} value={obj(v)} />;
        if (k === "rate_limits") return <RateLimitsCard key={k} value={obj(v)} />;
        if (k === "notify_interval_sec")
          return (
            <ScalarSelectCard
              key={k}
              settingKey={k}
              label="자동 알림 점검 주기"
              value={String(v ?? "")}
              options={NOTIFY_OPTS.map((n) => ({ value: String(n), label: `${n}초` }))}
              toValue={(s) => Number(s)}
            />
          );
        if (k === "safety_level")
          return (
            <ScalarSelectCard
              key={k}
              settingKey={k}
              label="안전 강도"
              value={String(v ?? "standard")}
              options={SAFETY_OPTS}
              toValue={(s) => s}
            />
          );
        if (!KNOWN.has(k)) return <RawCard key={k} settingKey={k} value={v} />;
        return null;
      })}
    </div>
  );
}

function obj(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
}

function CardShell({
  title,
  children,
  onSave,
  busy,
  saved,
  error,
}: {
  title: string;
  children: React.ReactNode;
  onSave: () => void;
  busy: boolean;
  saved: boolean;
  error: string | null;
}) {
  return (
    <Card padding="lg">
      <code className="font-bold text-primary-text">{title}</code>
      <div className="mt-3 flex flex-col gap-3">{children}</div>
      {error && <ErrorText className="mt-2">{error}</ErrorText>}
      <div className="mt-3 flex items-center gap-3">
        <Button onClick={onSave} disabled={busy} loading={busy} icon="save">
          저장
        </Button>
        {saved && (
          <span className="text-[length:var(--text-sm)] font-bold" style={{ color: "var(--success-text)" }}>
            저장됨
          </span>
        )}
      </div>
    </Card>
  );
}

function useSaver(key: string) {
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function save(value: unknown) {
    setBusy(true);
    setSaved(false);
    setError(null);
    try {
      const token = await getClientAccessToken();
      await putAdminSettings(token, { key, value });
      setSaved(true);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.status === 422
            ? "허용되지 않는 값이에요."
            : e.message
          : "저장하지 못했어요.",
      );
    } finally {
      setBusy(false);
    }
  }
  return { busy, saved, error, save, setSaved };
}

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[length:var(--text-sm)] font-semibold text-ink">{label}</span>
      <div className="w-[60%] max-w-[260px]">{children}</div>
    </div>
  );
}

function ModelsCard({ value }: { value: Record<string, unknown> }) {
  const [v, setV] = useState<Record<string, string>>(() => {
    const o: Record<string, string> = {};
    for (const f of MODEL_FIELDS) o[f.key] = String(value[f.key] ?? f.opts[0]);
    return o;
  });
  const s = useSaver("models");
  return (
    <CardShell title="models" onSave={() => void s.save(v)} busy={s.busy} saved={s.saved} error={s.error}>
      {MODEL_FIELDS.map((f) => (
        <FieldRow key={f.key} label={f.label}>
          <Select
            value={v[f.key]}
            onChange={(e) => {
              setV((p) => ({ ...p, [f.key]: e.target.value }));
              s.setSaved(false);
            }}
            options={f.opts.map((m) => ({ value: m, label: m }))}
          />
        </FieldRow>
      ))}
    </CardShell>
  );
}

function TogglesCard({ value }: { value: Record<string, unknown> }) {
  const [v, setV] = useState<Record<string, boolean>>(() => {
    const o: Record<string, boolean> = {};
    for (const f of TOGGLE_FIELDS) o[f.key] = !!value[f.key];
    return o;
  });
  const s = useSaver("feature_toggles");
  return (
    <CardShell title="feature_toggles" onSave={() => void s.save(v)} busy={s.busy} saved={s.saved} error={s.error}>
      {TOGGLE_FIELDS.map((f) => (
        <Switch
          key={f.key}
          label={f.label}
          checked={v[f.key]}
          onChange={(e) => {
            const on = e.target.checked;
            setV((p) => ({ ...p, [f.key]: on }));
            s.setSaved(false);
          }}
        />
      ))}
    </CardShell>
  );
}

function RateLimitsCard({ value }: { value: Record<string, unknown> }) {
  const [v, setV] = useState<Record<string, { limit: number; window: number }>>(() => {
    const o: Record<string, { limit: number; window: number }> = {};
    for (const b of RATE_BUCKETS) {
      const cur = obj(value[b.key]);
      o[b.key] = {
        limit: Number(cur.limit ?? 60),
        window: Number(cur.window ?? 60),
      };
    }
    return o;
  });
  const s = useSaver("rate_limits");
  return (
    <CardShell title="rate_limits" onSave={() => void s.save(v)} busy={s.busy} saved={s.saved} error={s.error}>
      {RATE_BUCKETS.map((b) => (
        <FieldRow key={b.key} label={b.label}>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={1}
              max={600}
              value={v[b.key].limit}
              onChange={(e) => {
                const n = Number(e.target.value);
                setV((p) => ({ ...p, [b.key]: { ...p[b.key], limit: n } }));
                s.setSaved(false);
              }}
              aria-label={`${b.label} 한도`}
              style={{ width: 88 }}
            />
            <span className="text-ink-3">회 /</span>
            <Select
              value={String(v[b.key].window)}
              onChange={(e) => {
                const n = Number(e.target.value);
                setV((p) => ({ ...p, [b.key]: { ...p[b.key], window: n } }));
                s.setSaved(false);
              }}
              options={WINDOW_OPTS.map((w) => ({ value: String(w), label: `${w}초` }))}
            />
          </div>
        </FieldRow>
      ))}
    </CardShell>
  );
}

function ScalarSelectCard({
  settingKey,
  label,
  value,
  options,
  toValue,
}: {
  settingKey: string;
  label: string;
  value: string;
  options: { value: string; label: string }[];
  toValue: (s: string) => unknown;
}) {
  const [v, setV] = useState(value);
  const s = useSaver(settingKey);
  return (
    <CardShell title={settingKey} onSave={() => void s.save(toValue(v))} busy={s.busy} saved={s.saved} error={s.error}>
      <FieldRow label={label}>
        <Select
          value={v}
          onChange={(e) => {
            setV(e.target.value);
            s.setSaved(false);
          }}
          options={options}
        />
      </FieldRow>
    </CardShell>
  );
}

function RawCard({ settingKey, value }: { settingKey: string; value: unknown }) {
  const [text, setText] = useState(() => JSON.stringify(value, null, 2));
  const s = useSaver(settingKey);
  function save() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      return;
    }
    void s.save(parsed);
  }
  return (
    <CardShell title={settingKey} onSave={save} busy={s.busy} saved={s.saved} error={s.error}>
      <Textarea
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          s.setSaved(false);
        }}
        rows={Math.min(10, text.split("\n").length + 1)}
        spellCheck={false}
        style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}
      />
    </CardShell>
  );
}
