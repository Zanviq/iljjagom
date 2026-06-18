-- 0014: ai_sessions.user_id — 총괄(overseer) AI 세션은 book 이 없으므로 사용자 귀속을 위해 user_id 추가.
-- (기존 designer/writer/editor 세션은 book_id 로 사용자 식별되지만, overseer 는 book 무관 학생 단위.)
-- 관리자 콘솔 트레이스에서 overseer 세션의 학생을 식별하고, 세션 소유권 검증(대화 연속)에 사용.

alter table public.ai_sessions
  add column if not exists user_id uuid references public.profiles(id) on delete set null;

create index if not exists idx_ai_sessions_user on public.ai_sessions(user_id);
