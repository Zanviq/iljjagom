import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import { SUPABASE_ANON_KEY, SUPABASE_URL } from "./env";

/**
 * 매 요청 Supabase 세션 쿠키를 갱신하고 현재 유저를 확인한다.
 * (Next 16 proxy / 구 middleware updateSession 패턴)
 * 주의: createServerClient 와 인증 호출 사이에 다른 로직을 넣지 않는다.
 *
 * 성능(05-기능수정 §05): `getUser()`는 매 요청 Supabase 인증 서버로 네트워크 왕복을
 * 보내 토큰을 검증한다(모든 페이지 이동마다). 이 프로젝트는 ES256(비대칭) JWT 라
 * `getClaims()`가 **JWKS 로컬 검증**(JWKS 1회 캐시)으로 끝나 원격 왕복을 없앤다.
 * 토큰 만료 시에만 내부적으로 refresh(네트워크) 1회 — 평상시 무왕복.
 */
export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value),
        );
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, options),
        );
      },
    },
  });

  // 로컬 비대칭 검증(원격 /auth/v1/user 왕복 제거). 유효 토큰이면 claims, 없으면 null.
  const { data } = await supabase.auth.getClaims();
  const user = data?.claims?.sub ? { id: data.claims.sub as string } : null;

  return { supabaseResponse, user };
}
