"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ApiError, postOnboarding } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import {
  buildDevToken,
  DEV_AUTH_COOKIE,
  type DevRole,
} from "@/lib/auth/devSession";
import { resolveDestinationFromToken, roleHome } from "@/lib/auth/guard";
import { isSupabaseConfigured } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";

export interface FormState {
  error?: string;
}

const WEEK = 60 * 60 * 24 * 7;

/** 개발 로그인(Supabase 미설정): dev 토큰 쿠키를 심고 역할 홈/온보딩으로 이동. */
export async function devLogin(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const role = String(formData.get("role") ?? "student") as DevRole;

  if (!email || !email.includes("@")) {
    return { error: "이메일을 올바르게 입력해 주세요." };
  }
  if (role !== "student" && role !== "teacher") {
    return { error: "역할을 선택해 주세요." };
  }

  const token = buildDevToken(email, role);
  const cookieStore = await cookies();
  cookieStore.set(DEV_AUTH_COOKIE, token, {
    // 개발 전용 토큰 — 클라이언트가 SSE/요청 Authorization 에 쓰기 위해 읽어야 함.
    httpOnly: false,
    sameSite: "lax",
    path: "/",
    maxAge: WEEK,
  });

  redirect(await resolveDestinationFromToken(token));
}

/** 온보딩 제출: POST /onboarding 후 역할 홈으로. 오류는 폼에 표시. */
export async function submitOnboarding(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const role = String(formData.get("role") ?? "") as "student" | "teacher";
  const classCodeRaw = String(formData.get("classCode") ?? "").trim();
  const guardianConsent = formData.get("guardianConsent") === "on";

  if (role !== "student" && role !== "teacher") {
    return { error: "역할을 선택해 주세요." };
  }
  if (role === "student" && !guardianConsent) {
    return { error: "보호자 동의가 필요해요." };
  }

  const token = await getAccessToken();
  if (!token) redirect("/login");

  try {
    await postOnboarding(token, {
      role,
      classCode: classCodeRaw || null,
      guardianConsent,
    });
  } catch (e) {
    if (e instanceof ApiError) return { error: e.message };
    throw e;
  }

  redirect(roleHome(role));
}

/** 로그아웃: Supabase 세션 종료 또는 dev 쿠키 삭제 후 /login. */
export async function logout() {
  if (isSupabaseConfigured) {
    const supabase = await createClient();
    await supabase.auth.signOut();
  } else {
    const cookieStore = await cookies();
    cookieStore.delete(DEV_AUTH_COOKIE);
  }
  redirect("/login");
}
