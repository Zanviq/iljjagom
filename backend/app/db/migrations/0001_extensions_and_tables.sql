-- 일짜곰 스키마 0001 — 확장 + 테이블
-- 권위 스키마: 03-기능명세서 §6 / 02-backend §3.
-- 모든 테이블은 0002_rls.sql 에서 RLS가 켜진다.

create extension if not exists "pgcrypto";   -- gen_random_uuid()
create extension if not exists vector;       -- pgvector (임베딩)

-- 역할/상태 enum
do $$ begin
  create type user_role as enum ('student', 'teacher', 'admin');
exception when duplicate_object then null; end $$;

do $$ begin
  create type book_status as enum ('planning', 'writing', 'done');
exception when duplicate_object then null; end $$;

do $$ begin
  create type chapter_mode as enum ('free', 'guided');
exception when duplicate_object then null; end $$;

do $$ begin
  create type review_status as enum ('pending', 'ok', 'revising');
exception when duplicate_object then null; end $$;

-- profiles: auth.users 와 1:1
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  role user_role not null default 'student',
  guardian_consent boolean not null default false,
  grade int,
  created_at timestamptz not null default now()
);

create table if not exists schools (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

-- classrooms: 학급. code = 학생 온보딩(classCode) 가입용 코드.
create table if not exists classrooms (
  id uuid primary key default gen_random_uuid(),
  school_id uuid references schools(id) on delete set null,
  teacher_id uuid not null references profiles(id) on delete cascade,
  name text not null,
  code text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists enrollments (
  classroom_id uuid not null references classrooms(id) on delete cascade,
  student_id uuid not null references profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (classroom_id, student_id)
);

create table if not exists prompts (
  id uuid primary key default gen_random_uuid(),
  classroom_id uuid not null references classrooms(id) on delete cascade,
  topic text not null,
  learning_objectives jsonb not null default '[]'::jsonb,
  assessment jsonb not null default '{}'::jsonb,
  language text not null default 'ko',
  created_at timestamptz not null default now()
);

create table if not exists books (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references profiles(id) on delete cascade,
  classroom_id uuid references classrooms(id) on delete set null,
  prompt_id uuid references prompts(id) on delete set null,
  status book_status not null default 'planning',
  title text,
  total_chapters_planned int,
  created_at timestamptz not null default now()
);

create table if not exists bibles (
  book_id uuid primary key references books(id) on delete cascade,
  data jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists chapters (
  id uuid primary key default gen_random_uuid(),
  book_id uuid not null references books(id) on delete cascade,
  idx int not null,
  mode chapter_mode not null default 'free',
  body text not null default '',
  illustration_path text,
  review_status review_status not null default 'pending',
  words jsonb not null default '[]'::jsonb,
  char_count int not null default 0,
  created_at timestamptz not null default now(),
  unique (book_id, idx)
);

-- 기획(인터뷰) 대화 로그
create table if not exists plan_messages (
  id uuid primary key default gen_random_uuid(),
  book_id uuid not null references books(id) on delete cascade,
  role text not null check (role in ('student', 'interviewer')),
  content text not null,
  created_at timestamptz not null default now()
);

-- RAG: Bible/본문 청크 임베딩 (gemini-embedding-001 = 768차원)
create table if not exists chapter_chunks (
  id uuid primary key default gen_random_uuid(),
  book_id uuid not null references books(id) on delete cascade,
  chapter_id uuid references chapters(id) on delete cascade,
  content text not null,
  embedding vector(768),
  created_at timestamptz not null default now()
);

create table if not exists learning_artifacts (
  id uuid primary key default gen_random_uuid(),
  book_id uuid not null references books(id) on delete cascade,
  chapter_id uuid references chapters(id) on delete cascade,
  type text not null check (type in ('vocab', 'quiz', 'essay', 'letter', 'emotion')),
  data jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  book_id uuid references books(id) on delete cascade,
  student_id uuid references profiles(id) on delete set null,
  type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists safety_flags (
  id uuid primary key default gen_random_uuid(),
  book_id uuid references books(id) on delete cascade,
  student_id uuid references profiles(id) on delete set null,
  source text not null,
  reason text not null,
  status text not null default 'open' check (status in ('open', 'reviewed')),
  created_at timestamptz not null default now()
);
