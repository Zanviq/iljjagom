import Link from "next/link";

import { Pending } from "@/components/admin/Pending";

/**
 * 세션 상세 = ReAct 흐름 시각화(06 §3.3): 스텝 타임라인(thought/skill/args/observation/tokens),
 * 이미지 생성 과정, awaiting_user 질문/응답. 계약 확정 후 실데이터 타임라인으로 교체.
 */
export default async function ConsoleSessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div>
      <Link href="/console/sessions" className="text-sm font-bold text-muted">
        ← AI 세션 목록
      </Link>
      <div className="mt-2">
        <Pending
          title={`세션 상세 · ${id}`}
          describe="ReAct 스텝 타임라인(thought·skill·args·observation·토큰·ms)과 이미지 생성 과정, awaiting_user 질문/응답."
          endpoint="GET /admin/sessions/{id}"
        />
      </div>
    </div>
  );
}
