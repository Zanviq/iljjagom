-- 일짜곰 스키마 0013 — profiles.status (관리자 사용자 관리: 소프트 비활성)
-- 근거: 03-추가기능/06 §3.2. 기본 active, 비활성은 deactivated.

alter table profiles
  add column if not exists status text not null default 'active'
  check (status in ('active', 'deactivated'));
