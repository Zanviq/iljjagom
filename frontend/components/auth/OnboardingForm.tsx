"use client";

import { useActionState, useState } from "react";

import { ErrorText } from "@/components/ui/ErrorText";
import { Field } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import { SubmitButton } from "@/components/ui/SubmitButton";
import { submitOnboarding, type FormState } from "@/lib/auth/actions";
import { cn } from "@/lib/cn";

const initial: FormState = {};

export function OnboardingForm() {
  const [state, formAction] = useActionState(submitOnboarding, initial);
  const [role, setRole] = useState<"student" | "teacher">("student");

  return (
    <form action={formAction} className="flex flex-col gap-6">
      <fieldset className="flex flex-col gap-2">
        <legend className="text-[length:var(--text-sm)] font-bold text-ink">나는…</legend>
        <div className="grid grid-cols-2 gap-3">
          {(["student", "teacher"] as const).map((r) => (
            <label
              key={r}
              className={cn(
                "flex cursor-pointer items-center justify-center gap-2 rounded-[var(--radius-input)] border-2 px-4 py-4 text-[length:var(--text-md)] font-bold transition",
                role === r
                  ? "border-primary bg-primary-tint text-primary-text"
                  : "border-line-strong bg-surface text-ink-2",
              )}
            >
              <input
                type="radio"
                name="role"
                value={r}
                checked={role === r}
                onChange={() => setRole(r)}
                className="sr-only"
              />
              <Icon name={r === "student" ? "smile" : "school"} size={18} />
              {r === "student" ? "학생이에요" : "선생님이에요"}
            </label>
          ))}
        </div>
      </fieldset>

      {role === "student" && (
        <>
          <Field
            label={
              <>
                학급 코드{" "}
                <span className="font-normal text-ink-3">(선생님께 받아요)</span>
              </>
            }
          >
            <Input
              name="classCode"
              type="text"
              placeholder="예) ABC123"
              autoCapitalize="characters"
              style={{ letterSpacing: ".1em" }}
            />
          </Field>

          <label className="flex items-start gap-3 rounded-[var(--radius-input)] bg-accent-tint p-4">
            <input
              name="guardianConsent"
              type="checkbox"
              className="mt-1 h-5 w-5 shrink-0 accent-[var(--primary)]"
            />
            <span className="text-[length:var(--text-sm)] text-ink">
              보호자가 일짜곰 사용에 동의했어요. (만 14세 미만은 보호자 동의가
              필요해요)
            </span>
          </label>
        </>
      )}

      {role === "teacher" && (
        <p className="rounded-[var(--radius-input)] bg-accent-tint p-4 text-[length:var(--text-sm)] text-accent-text">
          선생님은 로그인 후 학급을 만들고 발제를 낼 수 있어요.
        </p>
      )}

      {state.error && <ErrorText>{state.error}</ErrorText>}

      <SubmitButton fullWidth pendingText="설정 중…">시작하기</SubmitButton>
    </form>
  );
}
