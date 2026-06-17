"use client";

import { useActionState, useState } from "react";

import { buttonClass } from "@/components/ui/Button";
import { SubmitButton } from "@/components/ui/SubmitButton";
import { devLogin, type FormState } from "@/lib/auth/actions";
import { createClient } from "@/lib/supabase/client";

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
    <button
      onClick={signIn}
      disabled={loading}
      className={buttonClass("outline", "lg", "w-full")}
    >
      {loading ? "이동 중…" : "Google 계정으로 계속하기"}
    </button>
  );
}

function DevLogin() {
  const [state, formAction] = useActionState(devLogin, initial);
  const [role, setRole] = useState<"student" | "teacher">("student");

  return (
    <form action={formAction} className="flex flex-col gap-5">
      <p className="rounded-xl bg-accent/30 px-4 py-3 text-sm text-foreground">
        개발 로그인 모드예요. (Supabase 미설정) 이메일과 역할을 고르면 백엔드에
        <code className="mx-1">dev</code>토큰으로 접속해요.
      </p>

      <label className="flex flex-col gap-2">
        <span className="font-bold">이메일</span>
        <input
          name="email"
          type="email"
          required
          placeholder="me@school.kr"
          className="h-12 rounded-xl border-2 border-border bg-background px-4 text-lg"
        />
      </label>

      <fieldset className="flex flex-col gap-2">
        <legend className="font-bold">역할</legend>
        <div className="grid grid-cols-2 gap-3">
          {(["student", "teacher"] as const).map((r) => (
            <label
              key={r}
              className={`flex cursor-pointer items-center justify-center gap-2 rounded-xl border-2 px-4 py-3 text-lg font-bold transition ${
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
              {r === "student" ? "🧒 학생" : "👩‍🏫 교사"}
            </label>
          ))}
        </div>
      </fieldset>

      {state.error && (
        <p className="text-sm font-bold text-danger">{state.error}</p>
      )}

      <SubmitButton className="w-full" pendingText="접속 중…">
        시작하기
      </SubmitButton>
    </form>
  );
}
