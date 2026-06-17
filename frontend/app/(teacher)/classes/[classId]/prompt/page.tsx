import Link from "next/link";
import { notFound } from "next/navigation";

import { PromptForm } from "@/components/teacher/PromptForm";
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
    <section>
      <Link href="/classes" className="text-sm font-bold text-muted">
        ← 학급 목록
      </Link>
      <h1 className="mt-2 text-3xl font-extrabold">
        발제 {klass ? `· ${klass.name}` : ""}
      </h1>
      <p className="mt-1 text-muted">
        주제와 학습 목표를 정하면, 학생이 그 안에서 자기 이야기를 만들어요.
      </p>

      <div className="mt-6 grid gap-8 md:grid-cols-[1fr_20rem]">
        <PromptForm classId={classId} />

        <aside>
          <h2 className="text-lg font-bold">낸 발제 ({prompts.length})</h2>
          {prompts.length === 0 ? (
            <p className="mt-2 text-sm text-muted">아직 낸 발제가 없어요.</p>
          ) : (
            <ul className="mt-3 space-y-3">
              {prompts.map((p) => (
                <li
                  key={p.id}
                  className="rounded-card bg-surface p-4 ring-1 ring-border"
                >
                  <p className="font-bold">{p.topic}</p>
                  {p.learningObjectives.length > 0 && (
                    <ul className="mt-2 flex flex-wrap gap-1.5">
                      {p.learningObjectives.map((o, i) => (
                        <li
                          key={i}
                          className="rounded-full bg-secondary/15 px-2.5 py-0.5 text-xs text-secondary-strong"
                        >
                          {o}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </section>
  );
}
