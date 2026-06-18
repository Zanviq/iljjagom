import { notFound } from "next/navigation";

import { PromptForm } from "@/components/teacher/PromptForm";
import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { ApiError, getClasses, getPrompts } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { AssessmentType } from "@/lib/types";

const ASSESSMENT_LABEL: Record<AssessmentType, string> = {
  quiz: "퀴즈",
  essay: "독후감",
  none: "평가 없음",
};

const LANGUAGE_LABEL: Record<string, string> = {
  ko: "한국어",
  en: "English",
};

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
          {prompts.length === 0 ? (
            <p className="text-[length:var(--text-sm)] text-ink-3">
              아직 낸 발제가 없어요.
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {prompts.map((p) => (
                <Card key={p.id} padding="md">
                  <h4 className="text-[length:var(--text-base)] font-extrabold text-ink">
                    {p.topic}
                  </h4>
                  {p.learningObjectives.length > 0 && (
                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                      {p.learningObjectives.map((o, i) => (
                        <Chip key={i}>{o}</Chip>
                      ))}
                    </div>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge tone="primary" icon="clipboard-check">
                      {ASSESSMENT_LABEL[p.assessment.type]}
                    </Badge>
                    <Badge tone="info" icon="languages">
                      {LANGUAGE_LABEL[p.language] ?? p.language}
                    </Badge>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
