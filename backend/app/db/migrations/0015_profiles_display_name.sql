-- 0015: profiles.display_name — 학생 인사 개인화용 표시 이름.
-- 최초 로그인/온보딩 시 Supabase user_metadata(full_name|name)에서 채우고, 없으면 이메일 local-part 폴백.
-- GET /me 의 name 필드로 노출(없으면 null).

alter table public.profiles
  add column if not exists display_name text;
