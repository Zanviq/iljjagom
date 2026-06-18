import Link from "next/link";

import { buttonClass } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="max-w-xl">
        <span
          className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-[18px] bg-primary text-on-primary shadow-[var(--elev-pop)]"
          aria-hidden
        >
          <Icon name="book-heart" size={34} />
        </span>
        <h1
          className="ijg-wordmark text-ink"
          style={{ fontSize: 56, letterSpacing: "-.02em" }}
        >
          일짜곰
        </h1>
        <p className="mt-4 text-[length:var(--text-md)] text-ink-2 sm:text-[length:var(--text-lg)]">
          내가 만드는 이야기책. 직접 이야기를 짓고, 결말은 비밀로 펼쳐지고,
          읽으면서 배워요.
        </p>

        <div className="mt-10 flex justify-center">
          <Link
            href="/login"
            className={buttonClass("solid", "lg", "w-full max-w-xs")}
          >
            시작하기
            <Icon name="arrow-right" size={20} />
          </Link>
        </div>
      </div>
    </main>
  );
}
