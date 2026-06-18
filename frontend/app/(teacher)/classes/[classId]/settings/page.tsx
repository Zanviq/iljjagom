import { ClassSettingsForm } from "@/components/teacher/ClassSettingsForm";
import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { getClassSettings } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { ClassSettingsResponse } from "@/lib/types";

const FALLBACK: ClassSettingsResponse = {
  value: { safetyLevel: "standard", featureToggles: {} },
  defaults: { safetyLevel: "standard", featureToggles: {} },
};

export default async function ClassSettingsPage({
  params,
}: {
  params: Promise<{ classId: string }>;
}) {
  const { classId } = await params;
  const token = await getAccessToken();

  let settings: ClassSettingsResponse;
  try {
    settings = await getClassSettings(token, classId);
  } catch {
    // 미구현/오류 — 기본값으로 표시(저장은 graceful 안내).
    settings = FALLBACK;
  }

  return (
    <div>
      <TeacherHeader
        title="학급 설정"
        sub="안전 강도와 기능 사용을 학급에 맞게 조절해요."
      />
      <ClassSettingsForm classId={classId} initial={settings} />
    </div>
  );
}
