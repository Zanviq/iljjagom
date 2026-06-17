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
      <h1 className="text-3xl font-extrabold">안전</h1>
      <p className="mt-1 text-muted">
        전 학급의 미처리 안전 신호예요. 교사 검토(03)와 모델을 공유해요.
      </p>

      {pending ? (
        <EmptyState className="mt-6 text-left">
          <p className="font-bold text-foreground">백엔드 구현 대기</p>
          <p className="mt-2">
            계약은 확정됐고(<code>GET /admin/safety-flags</code>) 백엔드 구현이
            올라오면 자동으로 목록이 표시됩니다.
          </p>
        </EmptyState>
      ) : !flags || flags.length === 0 ? (
        <EmptyState className="mt-6">미처리 안전 신호가 없어요. 👍</EmptyState>
      ) : (
        <div className="mt-6">
          <SafetyFlagList flags={flags} />
        </div>
      )}
    </div>
  );
}
