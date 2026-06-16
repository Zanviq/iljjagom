import { SubmitButton } from "@/components/ui/SubmitButton";
import { getPrompts } from "@/lib/api";
import { getCurrentMe } from "@/lib/auth/guard";
import { getAccessToken } from "@/lib/auth/server";
import { startBook } from "@/lib/books/actions";
import type { Prompt } from "@/lib/types";

export default async function StudentHomePage() {
  const me = await getCurrentMe();
  const token = await getAccessToken();

  // 학급 미가입(또는 백엔드가 classId 미반영) — 안내만.
  if (!me?.classId) {
    return (
      <section>
        <Header className={null} />
        <div className="mt-6 rounded-card bg-surface p-6 ring-1 ring-border">
          <p className="text-lg font-bold">아직 학급에 들어가지 않았어요.</p>
          <p className="mt-2 text-muted">
            선생님께 받은 <strong>학급 코드</strong>로 가입하면 선생님이 낸
            이야기 주제(발제)로 새 책을 만들 수 있어요.
          </p>
        </div>
      </section>
    );
  }

  const { prompts } = await getPrompts(token, me.classId);

  return (
    <section>
      <Header className={me.className} />

      <h2 className="mb-4 mt-8 text-xl font-bold">
        새 이야기 시작하기{" "}
        <span className="font-normal text-muted">— 만들고 싶은 주제를 골라요</span>
      </h2>

      {prompts.length === 0 ? (
        <div className="rounded-card bg-surface p-6 ring-1 ring-border">
          <p className="text-muted">
            아직 선생님이 낸 발제가 없어요. 조금만 기다려 주세요!
          </p>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {prompts.map((p) => (
            <PromptCard key={p.id} prompt={p} />
          ))}
        </ul>
      )}
    </section>
  );
}

function Header({ className }: { className: string | null }) {
  return (
    <div>
      <h1 className="text-3xl font-extrabold">내 책장</h1>
      <p className="mt-1 text-muted">
        {className ? `${className} ` : ""}이야기를 만들고 읽어 봐요.
      </p>
    </div>
  );
}

function PromptCard({ prompt }: { prompt: Prompt }) {
  return (
    <li className="flex flex-col rounded-card bg-surface p-5 ring-1 ring-border">
      <h3 className="text-lg font-bold">{prompt.topic}</h3>
      {prompt.learningObjectives.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2">
          {prompt.learningObjectives.map((obj, i) => (
            <li
              key={i}
              className="rounded-full bg-secondary/15 px-3 py-1 text-sm text-secondary"
            >
              {obj}
            </li>
          ))}
        </ul>
      )}
      <form action={startBook} className="mt-5">
        <input type="hidden" name="promptId" value={prompt.id} />
        <SubmitButton size="md" className="w-full" pendingText="만드는 중…">
          이 주제로 새 책 만들기
        </SubmitButton>
      </form>
    </li>
  );
}
