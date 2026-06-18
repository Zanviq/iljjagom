import { SettingsEditor } from "@/components/admin/SettingsEditor";
import { Badge } from "@/components/ui/Badge";
import { ErrorText } from "@/components/ui/ErrorText";
import { getAdminSettings } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { AdminSettingsResponse } from "@/lib/types";

export default async function ConsoleSettingsPage() {
  const token = await getAccessToken();
  let data: AdminSettingsResponse | null = null;
  let error: string | null = null;
  try {
    data = await getAdminSettings(token);
  } catch (e) {
    error = e instanceof Error ? e.message : "설정을 불러오지 못했어요.";
  }

  return (
    <div>
      <p className="ijg-eyebrow mb-4 text-ink-3">
        모델 · 환경 설정 (시크릿 값은 노출/저장하지 않음)
      </p>

      {error ? (
        <ErrorText className="mt-2">{error}</ErrorText>
      ) : data ? (
        <>
          <h2 className="mb-3 text-[length:var(--text-md)] font-extrabold text-ink">
            환경변수 (존재 여부)
          </h2>
          <ul className="flex flex-wrap gap-2">
            {Object.entries(data.env).map(([k, present]) => (
              <li key={k}>
                <Badge
                  tone={present ? "success" : "danger"}
                  icon={present ? "check" : "x"}
                >
                  {k}
                </Badge>
              </li>
            ))}
          </ul>

          <h2 className="mb-3 mt-8 text-[length:var(--text-md)] font-extrabold text-ink">
            런타임 설정
          </h2>
          <SettingsEditor settings={data.settings} />
        </>
      ) : null}
    </div>
  );
}
