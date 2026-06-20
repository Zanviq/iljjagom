import "server-only";

import { cache } from "react";
import { redirect } from "next/navigation";

import { getAccessToken } from "@/lib/auth/server";
import { ApiError, getMe } from "@/lib/api";
import type { Me, Role } from "@/lib/types";

/** 역할별 홈 경로. */
export function roleHome(role: Role): string {
  switch (role) {
    case "teacher":
      return "/classes";
    case "admin":
      return "/console";
    default:
      return "/home";
  }
}

/**
 * 현재 사용자(GET /me). 토큰이 없거나 인증 실패(401)면 null.
 * (네트워크/서버 오류는 그대로 던져 상위에서 오류 화면을 보이게 한다.)
 *
 * React `cache`로 요청 단위 디듀프 — layout 가드와 page가 모두 호출해도
 * 백엔드 `/me`(JWKS 검증+프로필 조회)는 한 번만 왕복한다.
 */
export const getCurrentMe = cache(async (): Promise<Me | null> => {
  const token = await getAccessToken();
  if (!token) return null;
  try {
    return await getMe(token);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
});

/** 로그인 후 가야 할 목적지(온보딩 필요 여부 + 역할). */
export async function resolveDestinationFromToken(
  token: string,
): Promise<string> {
  try {
    const me = await getMe(token);
    return me.needsOnboarding ? "/onboarding" : roleHome(me.role);
  } catch {
    return "/login";
  }
}

/**
 * 역할 그룹 layout 가드. 권위 있는 역할 판별을 여기서 한다.
 * - 미로그인 → /login, 온보딩 필요 → /onboarding, 역할 불일치 → 자기 역할 홈.
 */
export async function requireRole(role: Role): Promise<Me> {
  const me = await getCurrentMe();
  if (!me) redirect("/login");
  if (me.needsOnboarding) redirect("/onboarding");
  if (me.role !== role) redirect(roleHome(me.role));
  return me;
}

/** 온보딩 페이지 가드: 로그인은 했지만 아직 역할이 없는 사용자만 머문다. */
export async function requireOnboarding(): Promise<Me> {
  const me = await getCurrentMe();
  if (!me) redirect("/login");
  if (!me.needsOnboarding) redirect(roleHome(me.role));
  return me;
}
