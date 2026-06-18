-- 일짜곰 스키마 0012 — 안전 게이트 강화 + 교사 검토 루프
-- 근거: 03-추가기능/03-안전-및-교사검토.md §4.1·§4.4.
-- letters 신설(보류 편지 원문 영속화) + safety_flags 상태머신/검토추적 확장 + RLS.

-- letters: 인물 편지 원문·답장·검토 상태 (현재 held 시 본문 유실 문제 해결)
create table if not exists letters (
  id uuid primary key default gen_random_uuid(),
  book_id uuid not null references books(id) on delete cascade,
  student_id uuid references profiles(id) on delete set null,
  recipient text not null,                 -- Bible character 이름(to)
  body text not null,                      -- 학생이 쓴 편지 원문
  status text not null default 'pending'
    check (status in ('pending', 'answered', 'held', 'approved', 'rejected')),
  reply text,                              -- AI/교사 답장(승인 시 확정)
  reply_source text,                       -- 'ai' | 'teacher'
  reviewed_by uuid references profiles(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists letters_book_idx on letters(book_id, created_at);
create index if not exists letters_status_idx on letters(status);

-- safety_flags 확장: 상태 머신(open→reviewed→resolved) + 검토 추적
alter table safety_flags drop constraint if exists safety_flags_status_check;
alter table safety_flags add constraint safety_flags_status_check
  check (status in ('open', 'reviewed', 'resolved'));

alter table safety_flags
  add column if not exists category    text,
  add column if not exists severity    text not null default 'normal',
  add column if not exists letter_id   uuid references letters(id) on delete set null,
  add column if not exists reviewed_by uuid references profiles(id) on delete set null,
  add column if not exists reviewed_at timestamptz,
  add column if not exists note        text;

create index if not exists safety_flags_status_idx on safety_flags(status, created_at);

-- RLS
alter table letters enable row level security;

drop policy if exists letters_select on letters;
create policy letters_select on letters for select using (can_access_book(book_id));

-- 학생: 자기 책 편지 생성(쓰기는 보통 서비스 롤이지만 유저 경로도 허용)
drop policy if exists letters_student_insert on letters;
create policy letters_student_insert on letters for insert
  with check (student_id = auth.uid() and can_access_book(book_id));

-- 검토(승인/반려): 담당 교사/admin (학생 본인 제외)
drop policy if exists letters_teacher_update on letters;
create policy letters_teacher_update on letters for update
  using (can_access_book(book_id) and not (student_id = auth.uid()))
  with check (can_access_book(book_id));

-- safety_flags UPDATE 정책 신설(현재 SELECT만 존재) — 담당 교사/admin
drop policy if exists safety_flags_teacher_update on safety_flags;
create policy safety_flags_teacher_update on safety_flags for update
  using (can_access_book(book_id)) with check (can_access_book(book_id));
