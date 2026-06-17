-- 일짜곰 스키마 0007 — 알림 / 런타임 설정 / 감사 로그
-- 근거: 03-추가기능/00 §3·§6·§7, 01 §3.2(0007). RLS는 0008에서 일괄 적용.

create table if not exists notifications (
  id uuid primary key default gen_random_uuid(),
  target_user_id uuid references profiles(id) on delete cascade,  -- null=role/broadcast
  target_role user_role,                                          -- null 가능
  is_broadcast boolean not null default false,
  title text not null,
  body text,
  level text not null default 'info' check (level in ('info', 'warn', 'error')),
  read_at timestamptz,
  created_at timestamptz not null default now()
);

-- app_settings: 런타임 설정(역할별 모델·토글·rate limit·알림주기). 00 §7.
-- 시크릿(API 키)은 절대 저장 금지 — 환경변수로만. 설정 패널은 "키 존재 여부"만 표시.
create table if not exists app_settings (
  key text primary key,
  value jsonb not null,
  updated_by uuid references profiles(id) on delete set null,
  updated_at timestamptz not null default now()
);

create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(),
  admin_id uuid references profiles(id) on delete set null,
  action text not null,
  target text,
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- 인덱스
create index if not exists notifications_user_idx on notifications(target_user_id, read_at);
create index if not exists notifications_role_idx on notifications(target_role, read_at);
create index if not exists notifications_created_idx on notifications(created_at desc);
create index if not exists audit_log_admin_idx on audit_log(admin_id, created_at desc);
create index if not exists audit_log_created_idx on audit_log(created_at desc);
