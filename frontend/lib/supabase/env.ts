/** Supabase 환경 설정 헬퍼. 비어 있으면 프론트는 "개발 로그인" 모드로 동작한다. */

export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

/** Supabase 자격이 모두 있으면 실제 Google OAuth 경로를 쓴다. */
export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
