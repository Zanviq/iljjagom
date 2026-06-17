-- 일짜곰 스키마 0011 — rate limit 무상태화용 카운터 테이블
-- 근거: 03-추가기능/01 §3.4(a). 멀티 워커에서도 한도가 정합하도록 프로세스 메모리 대신 DB로.
-- 시스템 카운터 — 서비스 롤(백엔드)만 접근. 유저 정책 없음(RLS on, 정책 미정의 = 차단).

create table if not exists rate_hits (
  id uuid primary key default gen_random_uuid(),
  bucket text not null,
  user_id uuid not null,
  created_at timestamptz not null default now()
);

create index if not exists rate_hits_lookup on rate_hits(bucket, user_id, created_at);

alter table rate_hits enable row level security;
