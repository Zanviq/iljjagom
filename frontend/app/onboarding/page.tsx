import { OnboardingForm } from "@/components/auth/OnboardingForm";
import { requireOnboarding } from "@/lib/auth/guard";

export default async function OnboardingPage() {
  const me = await requireOnboarding();

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-md rounded-[var(--radius-card)] border border-line bg-surface p-8 shadow-[var(--elev-md)]">
        <div className="mb-6 text-center">
          <h1 className="text-[length:var(--text-xl)] font-extrabold text-ink">
            처음 오셨네요!
          </h1>
          <p className="mt-2 text-ink-2">
            {me.email} 님, 시작하기 전에 몇 가지만 알려 주세요.
          </p>
        </div>
        <OnboardingForm />
      </div>
    </main>
  );
}
