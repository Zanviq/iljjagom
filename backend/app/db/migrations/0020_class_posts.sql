-- 학생/15 §4 · 14: 학급 게시판(발표/소개). 완성 책을 학급에 발표, 교사 승인 후 공개.
-- 게시판 공개 정책은 학급별 토글(기본 false=승인 후 공개, 00 §7 확정).
alter table public.classrooms
  add column if not exists board_auto_publish boolean not null default false;

create table if not exists public.class_posts (
  id uuid primary key default gen_random_uuid(),
  classroom_id uuid not null references public.classrooms(id) on delete cascade,
  book_id      uuid not null references public.books(id) on delete cascade,
  student_id   uuid not null references public.profiles(id) on delete cascade,
  title        text not null,
  intro        text,
  snapshot     jsonb not null default '{}'::jsonb,
  status       text not null default 'pending' check (status in ('pending', 'published', 'rejected')),
  reviewed_by  uuid references public.profiles(id) on delete set null,
  reviewed_at  timestamptz,
  review_note  text,
  created_at   timestamptz not null default now(),
  unique (book_id)
);
create index if not exists class_posts_class_idx on public.class_posts(classroom_id, status, created_at);

alter table public.class_posts enable row level security;

-- 읽기: published 는 같은 학급 멤버(교사/학생), 그 외(pending/rejected)는 작성 학생·담당 교사·admin.
create policy class_posts_select on public.class_posts for select using (
  is_admin()
  or student_id = auth.uid()
  or exists (select 1 from public.classrooms c where c.id = classroom_id and c.teacher_id = auth.uid())
  or (status = 'published' and exists (
        select 1 from public.enrollments e
        where e.classroom_id = classroom_id and e.student_id = auth.uid()))
);

-- 작성: 본인 책 + 해당 학급 소속 학생만.
create policy class_posts_student_insert on public.class_posts for insert
  with check (student_id = auth.uid() and can_access_book(book_id)
              and exists (select 1 from public.enrollments e
                          where e.classroom_id = classroom_id and e.student_id = auth.uid()));

-- 재제출(본인) / 승인·반려(담당 교사·admin).
create policy class_posts_student_update on public.class_posts for update
  using (student_id = auth.uid()) with check (student_id = auth.uid());
create policy class_posts_teacher_update on public.class_posts for update
  using (is_admin() or exists (select 1 from public.classrooms c
                               where c.id = classroom_id and c.teacher_id = auth.uid()))
  with check (is_admin() or exists (select 1 from public.classrooms c
                                    where c.id = classroom_id and c.teacher_id = auth.uid()));
