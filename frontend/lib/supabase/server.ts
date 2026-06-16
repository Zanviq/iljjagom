import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

import { SUPABASE_ANON_KEY, SUPABASE_URL } from "./env";

/**
 * 서버(서버 컴포넌트·서버 액션·라우트 핸들러)용 Supabase 클라이언트.
 * Next 16: cookies()는 async. setAll은 서버 컴포넌트에서 호출 시 무시될 수 있어
 * try/catch로 감싼다(세션 갱신은 proxy.ts가 담당).
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options),
          );
        } catch {
          // 서버 컴포넌트에서 호출됨 — proxy가 세션을 갱신하므로 무시 가능.
        }
      },
    },
  });
}
