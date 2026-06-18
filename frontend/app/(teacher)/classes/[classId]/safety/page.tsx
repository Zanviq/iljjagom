import Link from "next/link";

import { SafetyReview } from "@/components/teacher/SafetyReview";
import { EmptyState } from "@/components/ui/EmptyState";
import { getClasses, getClassLetters, getClassSafetyFlags } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { Letter, SafetyFlag } from "@/lib/types";

/**
 * 교사 안전 검토(03): 보류 편지 승인/미발송 + 안전 신호 종결.
 * 계약 확정(03 §4.2)됐으나 백엔드 구현 진행 중 → 엔드포인트 미노출 시 graceful 안내.
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
    <section>
      <Link href="/classes" className="text-sm font-bold text-muted">
        ← 학급 목록
      </Link>
      <h1 className="mt-2 text-3xl font-extrabold">
        안전 검토 {klass ? `· ${klass.name}` : ""}
      </h1>
      <p className="mt-1 text-muted">
        보류된 편지와 안전 신호를 확인하고 처리해요.
      </p>

      {pending ? (
        <EmptyState className="mt-6 text-left">
          <p className="font-bold text-foreground">백엔드 구현 대기</p>
          <p className="mt-2">
            계약은 확정됐어요(<code>GET /classes/{"{id}"}/safety-flags</code>,{" "}
            <code>/letters</code>). 백엔드 구현이 올라오면 검토 목록이 자동으로
            표시됩니다.
          </p>
        </EmptyState>
      ) : (
        <div className="mt-6">
          <SafetyReview letters={letters} flags={flags} />
        </div>
      )}
    </section>
  );
}
