import { redirect } from "next/navigation";

import { LoginForm } from "@/components/auth/LoginForm";
import { resolveDestinationFromToken } from "@/lib/auth/guard";
import { getAccessToken } from "@/lib/auth/server";
import { isSupabaseConfigured } from "@/lib/supabase/env";

export default async function LoginPage() {
  // 이미 로그인 상태면 역할 홈/온보딩으로.
  const token = await getAccessToken();
  if (token) {
    const dest = await resolveDestinationFromToken(token);
    if (dest !== "/login") redirect(dest);
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-md rounded-card bg-surface p-8 shadow-sm ring-1 ring-border">
        <div className="mb-8 text-center">
          <p className="text-5xl" aria-hidden>
            🐻
          </p>
          <h1 className="mt-3 text-3xl font-extrabold">일짜곰에 오신 걸 환영해요</h1>
          <p className="mt-2 text-muted">로그인하고 나만의 이야기책을 만들어요.</p>
        </div>
        <LoginForm supabaseEnabled={isSupabaseConfigured} />
      </div>
    </main>
  );
}
