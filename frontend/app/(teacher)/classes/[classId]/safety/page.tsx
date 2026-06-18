import { SafetyReview } from "@/components/teacher/SafetyReview";
import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { getClasses, getClassLetters, getClassSafetyFlags } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { Letter, SafetyFlag } from "@/lib/types";

/**
 * 교사 안전 검토(03): 보류 편지 승인/미발송 + 안전 신호 종결.
 */
export default async function ClassSafetyPage({
  params,
}: {
  params: Promise<{ classId: string }>;
}) {
  const { classId } = await params;
  const token = await getAccessToken();

  const { classes } = await getClasses(token).catch(() => ({ classes: [] }));
  const klass = classes.find((c) => c.id === classId);

  let flags: SafetyFlag[] = [];
  let letters: Letter[] = [];
  let pending = false;
  try {
    const [f, l] = await Promise.all([
      getClassSafetyFlags(token, classId, { status: "open" }),
      getClassLetters(token, classId, "held"),
    ]);
    flags = f.flags;
    letters = l.letters;
  } catch {
    // 엔드포인트 미구현/미노출(구현 진행 중) → 대기 안내.
    pending = true;
  }

  return (
    <div>
      <TeacherHeader
        title={`안전 검토${klass ? ` · ${klass.name}` : ""}`}
        sub="확인이 필요한 신호를 검토하고 처리해요."
      />

      {pending ? (
        <EmptyState icon="shield-check" title="백엔드 구현 대기">
          계약은 확정됐어요. 백엔드 구현이 올라오면 검토 목록이 자동으로
          표시됩니다.
        </EmptyState>
      ) : (
        <SafetyReview letters={letters} flags={flags} />
      )}
    </div>
  );
}
