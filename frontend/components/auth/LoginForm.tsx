"use client";

import { useActionState, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ErrorText } from "@/components/ui/ErrorText";
import { Field } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import { SubmitButton } from "@/components/ui/SubmitButton";
import { devLogin, type FormState } from "@/lib/auth/actions";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/cn";

const initial: FormState = {};

export function LoginForm({ supabaseEnabled }: { supabaseEnabled: boolean }) {
  if (supabaseEnabled) return <GoogleLogin />;
  return <DevLogin />;
}

function GoogleLogin() {
  const [loading, setLoading] = useState(false);

  async function signIn() {
    setLoading(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${location.origin}/auth/callback`,
        // 공유 기기(학교) 대비 + 자동 재로그인 방지: 항상 Google 계정 선택을 띄운다.
        queryParams: { prompt: "select_account" },
      },
    });
    if (error) setLoading(false);
  }

  return (
    <Button
      variant="outline"
      size="lg"
      fullWidth
      icon="log-in"
      loading={loading}
      onClick={signIn}
    >
      {loading ? "이동 중…" : "Google 계정으로 계속하기"}
    </Button>
  );
}

function DevLogin() {
  const [state, formAction] = useActionState(devLogin, initial);
  const [role, setRole] = useState<"student" | "teacher">("student");

  return (
    <form action={formAction} className="flex flex-col gap-5">
      <p className="rounded-[var(--radius-input)] bg-accent-tint px-4 py-3 text-[length:var(--text-sm)] text-accent-text">
        개발 로그인 모드예요. (Supabase 미설정) 이메일과 역할을 고르면 백엔드에
        <code className="mx-1">dev</code>토큰으로 접속해요.
      </p>

      <Field label="이메일">
        <Input name="email" type="email" required icon="mail" placeholder="me@school.kr" />
      </Field>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-[length:var(--text-sm)] font-bold text-ink">역할</legend>
        <div className="grid grid-cols-2 gap-3">
          {(["student", "teacher"] as const).map((r) => (
            <label
              key={r}
              className={cn(
                "flex cursor-pointer items-center justify-center gap-2 rounded-[var(--radius-input)] border-2 px-4 py-3 text-[length:var(--text-md)] font-bold transition",
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
              {r === "student" ? "학생" : "교사"}
            </label>
          ))}
        </div>
      </fieldset>

      {state.error && <ErrorText>{state.error}</ErrorText>}

      <SubmitButton fullWidth pendingText="접속 중…">시작하기</SubmitButton>
    </form>
  );
}
