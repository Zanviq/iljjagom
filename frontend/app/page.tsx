import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="max-w-xl">
        <p className="mb-4 text-6xl" aria-hidden>
          🐻📖
        </p>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          일짜곰
        </h1>
        <p className="mt-4 text-lg text-muted sm:text-xl">
          내가 만드는 이야기책. 직접 이야기를 짓고, 결말은 비밀로 펼쳐지고,
          읽으면서 배워요.
        </p>

        <div className="mt-10 flex flex-col items-center gap-4">
          <Link
            href="/login"
            className="flex h-14 w-full max-w-xs items-center justify-center rounded-card bg-primary px-8 text-xl font-bold text-primary-foreground shadow-sm transition hover:brightness-105 active:scale-[0.98]"
          >
            시작하기
          </Link>
        </div>
      </div>
    </main>
  );
}
