-- 일짜곰 스키마 0006 — AI 세션 / ReAct 트레이스 / 통합 대화 / 토큰 사용
-- 근거: 03-추가기능/00 §3·§5, 01 §3.2(0006). RLS는 0008에서 일괄 적용.
-- 관측 가능성(Observability): 모든 AI 동작을 테이블에 영속화해 관리자 페이지가 읽는다.

-- ai_sessions: AI 작업 1단위 (ReAct 루프 1회 또는 단일 작업)
do $$ begin
  create type ai_session_status as enum ('running', 'awaiting_user', 'done', 'error');
exception when duplicate_object then null; end $$;

create table if not exists ai_sessions (
  id uuid primary key default gen_random_uuid(),
  book_id uuid references books(id) on delete cascade,
  role text not null,            -- designer|writer|editor|chat|letter ...
  model text,                    -- 실제 사용 모델(추적)
  status ai_session_status not null default 'running',
  summary text,
  error text,
  started_at timestamptz not null default now(),
  ended_at timestamptz
);

-- ai_steps: ReAct 스텝(트레이스). 00 §5 스키마.
create table if not exists ai_steps (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references ai_sessions(id) on delete cascade,
  idx int not null,
  thought text,
  skill text,
  args jsonb not null default '{}'::jsonb,
  observation jsonb not null default '{}'::jsonb,
  tokens_in int not null default 0,
  tokens_out int not null default 0,
  ms int,
  created_at timestamptz not null default now(),
  unique (session_id, idx)
);

-- messages: 통합 대화(기획/편지/튜터). plan_messages 후속(과도기 병행).
create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  book_id uuid references books(id) on delete cascade,
  user_id uuid references profiles(id) on delete set null,
  role text not null check (role in ('user', 'ai', 'system')),
  kind text not null default 'plan',   -- plan|letter|tutor ...
  content text not null,
  session_id uuid references ai_sessions(id) on delete set null,
  created_at timestamptz not null default now()
);

-- token_usage: 호출별 토큰/비용
create table if not exists token_usage (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references ai_sessions(id) on delete cascade,
  model text not null,
  tokens_in int not null default 0,
  tokens_out int not null default 0,
  est_cost numeric(12, 6) not null default 0,
  created_at timestamptz not null default now()
);

-- 인덱스 (관리자 실시간/필터·집계)
create index if not exists ai_sessions_book_idx on ai_sessions(book_id, started_at desc);
create index if not exists ai_sessions_status_idx on ai_sessions(status);
create index if not exists ai_steps_session_idx on ai_steps(session_id, idx);
create index if not exists messages_book_idx on messages(book_id, created_at);
create index if not exists messages_session_idx on messages(session_id);
create index if not exists token_usage_session_idx on token_usage(session_id);
create index if not exists token_usage_created_idx on token_usage(created_at);
