import { NextResponse, type NextRequest } from "next/server";

import { DEV_AUTH_COOKIE } from "@/lib/auth/devSession";
import { isSupabaseConfigured } from "@/lib/supabase/env";
import { updateSession } from "@/lib/supabase/proxy";

/**
 * (Next 16 proxy / 구 middleware) 매 요청 세션을 갱신하고 낙관적 인증 가드를 건다.
 * - 권위 있는 역할 판별은 각 역할 그룹 layout(서버 컴포넌트)에서 GET /me 로 한다.
 * - 비로그인 사용자가 보호 라우트에 접근하면 /login 으로 보낸다.
 */
const PUBLIC_PATHS = ["/login", "/auth"];

function isPublic(pathname: string): boolean {
  if (pathname === "/") return true;
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

function redirectToLogin(request: NextRequest) {
  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  return NextResponse.redirect(url);
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isSupabaseConfigured) {
    const { supabaseResponse, user } = await updateSession(request);
    if (!user && !isPublic(pathname)) return redirectToLogin(request);
    return supabaseResponse;
  }

  // 개발 모드(Supabase 미설정): dev 쿠키로 낙관적 인증.
  const hasDev = Boolean(request.cookies.get(DEV_AUTH_COOKIE)?.value);
  if (!hasDev && !isPublic(pathname)) return redirectToLogin(request);
  return NextResponse.next();
}

export const config = {
  matcher: [
    // _next 내부와 정적 파일을 제외한 모든 라우트.
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
