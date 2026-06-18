"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorText } from "@/components/ui/ErrorText";
import { Textarea } from "@/components/ui/Textarea";
import { ApiError, putAdminSettings } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";

/**
 * 런타임 설정 편집(추가기능 06). 키별 JSON 값을 편집해 PUT /admin/settings.
 * 시크릿은 settings 에 없음(env 존재여부만 별도 표시). 잘못된 JSON 은 저장 막음.
 */
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
      {keys.map((k) => (
        <SettingRow key={k} settingKey={k} value={settings[k]} />
      ))}
    </div>
  );
}

function SettingRow({
  settingKey,
  value,
}: {
  settingKey: string;
  value: unknown;
}) {
  const router = useRouter();
  const [text, setText] = useState(() => JSON.stringify(value, null, 2));
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      setError("JSON 형식이 올바르지 않아요.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      await putAdminSettings(token, { key: settingKey, value: parsed });
      setSaved(true);
      router.refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "저장하지 못했어요.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card padding="md">
      <div className="flex items-center justify-between">
        <code className="font-bold text-primary-text">{settingKey}</code>
        {saved && (
          <span
            className="text-[length:var(--text-sm)] font-bold"
            style={{ color: "var(--success-text)" }}
          >
            저장됨
          </span>
        )}
      </div>
      <Textarea
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setSaved(false);
        }}
        rows={Math.min(10, text.split("\n").length + 1)}
        spellCheck={false}
        className="mt-2"
        style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}
      />
      {error && <ErrorText className="mt-2">{error}</ErrorText>}
      <Button onClick={() => void save()} disabled={pending} loading={pending} className="mt-3">
        {pending ? "저장 중…" : "저장"}
      </Button>
    </Card>
  );
}
