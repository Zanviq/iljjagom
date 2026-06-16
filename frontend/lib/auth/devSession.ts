/**
 * 개발 로그인 세션 (Supabase 미설정 시).
 * 백엔드가 DEV_AUTH=true(+JWT 시크릿 없음)일 때 받는 `dev:<email>:<role>` 토큰을
 * 쿠키에 담아 두고, API 호출 시 Bearer 로 보낸다. 키 없이 P1 슬라이스를 끝까지 돌리기 위한 용도.
 */
import type { Role } from "@/lib/types";

export const DEV_AUTH_COOKIE = "il_dev_auth";

export type DevRole = "student" | "teacher" | "admin";

export function buildDevToken(email: string, role: DevRole): string {
  return `dev:${email.trim().toLowerCase()}:${role}`;
}

export function parseDevToken(
  token: string | undefined | null,
): { email: string; role: Role } | null {
  if (!token || !token.startsWith("dev:")) return null;
  const parts = token.split(":");
  if (parts.length < 3 || !parts[1] || !parts[2]) return null;
  return { email: parts[1], role: parts[2] as Role };
}
