import { SafetyFlagList } from "@/components/admin/SafetyFlagList";
import { EmptyState } from "@/components/ui/EmptyState";
import { getAdminSafetyFlags } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { SafetyFlag } from "@/lib/types";

/**
 * 안전 탭(06 §3.6 / 03 공유): 전 학급 안전 신호. 계약 확정(03 §4.2)됐으나 백엔드 구현 진행 중이라
 * 엔드포인트 미노출일 수 있음 → graceful 안내.
 */
export default async function ConsoleSafetyPage() {
  const token = await getAccessToken();

  let flags: SafetyFlag[] | null = null;
  let pending = false;
  try {
    ({ flags } = await getAdminSafetyFlags(token, "open"));
  } catch {
    pending = true;
  }

  return (
    <div>
      <p className="ijg-eyebrow mb-4 text-ink-3">
        안전 · 전 학급 미처리 신호 (교사 검토와 모델 공유)
      </p>

      {pending ? (
        <EmptyState icon="clock" title="백엔드 구현 대기">
          계약은 확정됐어요. 백엔드 구현이 올라오면 목록이 자동으로 표시됩니다.
        </EmptyState>
      ) : !flags || flags.length === 0 ? (
        <EmptyState icon="shield-check" title="미처리 안전 신호가 없어요" />
      ) : (
        <SafetyFlagList flags={flags} />
      )}
    </div>
  );
}
