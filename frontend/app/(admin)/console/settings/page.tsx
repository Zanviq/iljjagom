import { SettingsEditor } from "@/components/admin/SettingsEditor";
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
      <h1 className="text-3xl font-extrabold">설정</h1>
      <p className="mt-1 text-muted">
        역할별 모델·런타임 수치를 편집해요. 시크릿 값은 노출/저장하지 않아요.
      </p>

      {error ? (
        <ErrorText className="mt-6">{error}</ErrorText>
      ) : data ? (
        <>
          <h2 className="mb-3 mt-6 text-lg font-bold">환경변수 (존재 여부)</h2>
          <ul className="flex flex-wrap gap-2">
            {Object.entries(data.env).map(([k, present]) => (
              <li
                key={k}
                className={`rounded-full px-3 py-1 text-sm font-bold ${
                  present
                    ? "bg-success/15 text-success-strong"
                    : "bg-danger/10 text-danger"
                }`}
              >
                {k} {present ? "✓" : "✗"}
              </li>
            ))}
          </ul>

          <h2 className="mb-3 mt-8 text-lg font-bold">런타임 설정</h2>
          <SettingsEditor settings={data.settings} />
        </>
      ) : null}
    </div>
  );
}
