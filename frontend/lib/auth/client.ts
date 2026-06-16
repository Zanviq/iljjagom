"use client";

import { DEV_AUTH_COOKIE } from "@/lib/auth/devSession";
import { createClient } from "@/lib/supabase/client";
import { isSupabaseConfigured } from "@/lib/supabase/env";

/**
 * 클라이언트에서 백엔드 호출/SSE에 쓸 Bearer 토큰을 가져온다.
 * - Supabase 설정 시: 브라우저 세션 access_token.
 * - 개발 모드: 비-httpOnly 쿠키(dev:email:role)에서 읽는다.
 */
export async function getClientAccessToken(): Promise<string | null> {
  if (isSupabaseConfigured) {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${DEV_AUTH_COOKIE}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]) : null;
}
