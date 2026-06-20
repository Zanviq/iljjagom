import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";

import { DEV_AUTH_COOKIE } from "@/lib/auth/devSession";
import { isSupabaseConfigured } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";

/**
 * 백엔드 호출에 쓸 Bearer 토큰을 서버에서 해석한다.
 * - Supabase 설정 시: 세션 access_token.
 * - 개발 모드: 개발 토큰 쿠키(dev:email:role).
 * (토큰은 백엔드가 검증하므로 여기서는 추출만 한다.)
 *
 * React `cache`로 한 번의 서버 렌더(요청) 동안 결과를 디듀프한다 —
 * layout·page가 각자 토큰을 읽어도 Supabase getSession은 1회만 실행된다.
 */
export const getAccessToken = cache(async (): Promise<string | null> => {
  if (isSupabaseConfigured) {
    const supabase = await createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }
  const cookieStore = await cookies();
  return cookieStore.get(DEV_AUTH_COOKIE)?.value ?? null;
});

/** 로그인 여부(낙관적). 서버 컴포넌트/액션에서 사용. */
export async function hasSession(): Promise<boolean> {
  if (isSupabaseConfigured) {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    return Boolean(user);
  }
  const cookieStore = await cookies();
  return Boolean(cookieStore.get(DEV_AUTH_COOKIE)?.value);
}
