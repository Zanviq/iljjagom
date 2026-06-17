import Link from "next/link";

import { getClasses } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function TeacherClassesPage() {
  const token = await getAccessToken();
  const { classes } = await getClasses(token);

  return (
    <section>
      <h1 className="text-3xl font-extrabold">내 학급</h1>
      <p className="mt-1 text-muted">
        학급 코드를 학생에게 알려 주고, 발제(이야기 주제)를 내요.
      </p>

      {classes.length === 0 ? (
        <div className="mt-6 rounded-card bg-surface p-6 ring-1 ring-border">
          <p className="text-muted">아직 학급이 없어요.</p>
        </div>
      ) : (
        <ul className="mt-6 grid gap-4 sm:grid-cols-2">
          {classes.map((c) => (
            <li
              key={c.id}
              className="flex flex-col rounded-card bg-surface p-5 ring-1 ring-border"
            >
              <h2 className="text-xl font-bold">{c.name}</h2>
              <p className="mt-1 text-sm text-muted">학생 {c.studentCount}명</p>

              <div className="mt-4 rounded-xl bg-accent/20 px-4 py-3">
                <p className="text-xs font-bold text-muted">학급 코드</p>
                <p className="text-2xl font-extrabold tracking-widest">
                  {c.code}
                </p>
              </div>

              <div className="mt-4 flex gap-2">
                <Link
                  href={`/classes/${c.id}/prompt`}
                  className="inline-flex h-12 flex-1 items-center justify-center rounded-card bg-primary px-5 font-bold text-primary-foreground transition hover:brightness-105"
                >
                  발제 만들기 / 보기
                </Link>
                <Link
                  href={`/classes/${c.id}/dashboard`}
                  className="inline-flex h-12 items-center justify-center rounded-card border-2 border-border bg-surface px-5 font-bold transition hover:border-primary"
                >
                  대시보드
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
