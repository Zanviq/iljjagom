import { notFound } from "next/navigation";

import { PromptForm } from "@/components/teacher/PromptForm";
import { PromptList } from "@/components/teacher/PromptList";
import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { ApiError, getClasses, getPrompts } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function PromptPage({
  params,
}: {
  params: Promise<{ classId: string }>;
}) {
  const { classId } = await params;
  const token = await getAccessToken();

  const [{ classes }, promptsResult] = await Promise.all([
    getClasses(token),
    getPrompts(token, classId).catch((e) => {
      if (e instanceof ApiError && e.status === 404) notFound();
      throw e;
    }),
  ]);

  const klass = classes.find((c) => c.id === classId);
  const prompts = promptsResult.prompts;

  return (
    <div>
      <TeacherHeader
        title={`발제${klass ? ` · ${klass.name}` : ""}`}
        sub="이야기 주제와 학습 목표를 정해 학급에 내요."
      />

      <div className="grid items-start gap-[22px] [grid-template-columns:1fr] md:[grid-template-columns:1.3fr_1fr]">
        <PromptForm classId={classId} />

        <div>
          <p className="ijg-eyebrow mb-3 text-ink-3">낸 발제 ({prompts.length})</p>
          <PromptList classId={classId} initial={prompts} />
        </div>
      </div>
    </div>
  );
}
