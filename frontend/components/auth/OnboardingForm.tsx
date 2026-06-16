"use client";

import { useActionState, useState } from "react";

import { SubmitButton } from "@/components/ui/SubmitButton";
import { submitOnboarding, type FormState } from "@/lib/auth/actions";

const initial: FormState = {};

export function OnboardingForm() {
  const [state, formAction] = useActionState(submitOnboarding, initial);
  const [role, setRole] = useState<"student" | "teacher">("student");

  return (
    <form action={formAction} className="flex flex-col gap-6">
      <fieldset className="flex flex-col gap-2">
        <legend className="font-bold">나는…</legend>
        <div className="grid grid-cols-2 gap-3">
          {(["student", "teacher"] as const).map((r) => (
            <label
              key={r}
              className={`flex cursor-pointer items-center justify-center gap-2 rounded-xl border-2 px-4 py-4 text-lg font-bold transition ${
                role === r
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-surface"
              }`}
            >
              <input
                type="radio"
                name="role"
                value={r}
                checked={role === r}
                onChange={() => setRole(r)}
                className="sr-only"
              />
              {r === "student" ? "🧒 학생이에요" : "👩‍🏫 선생님이에요"}
            </label>
          ))}
        </div>
      </fieldset>

      {role === "student" && (
        <>
          <label className="flex flex-col gap-2">
            <span className="font-bold">
              학급 코드{" "}
              <span className="font-normal text-muted">(선생님께 받아요)</span>
            </span>
            <input
              name="classCode"
              type="text"
              placeholder="예) ABC123"
              autoCapitalize="characters"
              className="h-12 rounded-xl border-2 border-border bg-background px-4 text-lg tracking-widest"
            />
          </label>

          <label className="flex items-start gap-3 rounded-xl bg-accent/20 p-4">
            <input
              name="guardianConsent"
              type="checkbox"
              className="mt-1 h-5 w-5 shrink-0"
            />
            <span className="text-sm">
              보호자가 일짜곰 사용에 동의했어요. (만 14세 미만은 보호자 동의가
              필요해요)
            </span>
          </label>
        </>
      )}

      {role === "teacher" && (
        <p className="rounded-xl bg-accent/20 p-4 text-sm text-muted">
          선생님은 로그인 후 학급을 만들고 발제를 낼 수 있어요.
        </p>
      )}

      {state.error && (
        <p className="text-sm font-bold text-danger">{state.error}</p>
      )}

      <SubmitButton className="w-full" pendingText="설정 중…">
        시작하기
      </SubmitButton>
    </form>
  );
}
