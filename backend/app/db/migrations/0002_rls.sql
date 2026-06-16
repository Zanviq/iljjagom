-- 일짜곰 스키마 0002 — Row Level Security
-- 학생: 자기 books/chapters/artifacts 만. 교사: 자기 classrooms 에 속한 책만.
-- 관리자: profiles.role='admin' 이면 전체. 서비스 롤(워커)은 RLS를 우회한다.

-- 모든 테이블 RLS 활성화
alter table profiles            enable row level security;
alter table schools             enable row level security;
alter table classrooms          enable row level security;
alter table enrollments         enable row level security;
alter table prompts             enable row level security;
alter table books               enable row level security;
alter table bibles              enable row level security;
alter table chapters            enable row level security;
alter table plan_messages       enable row level security;
alter table chapter_chunks      enable row level security;
alter table learning_artifacts  enable row level security;
alter table events              enable row level security;
alter table safety_flags        enable row level security;

-- 헬퍼: 현재 유저가 admin 인가
create or replace function is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from profiles p where p.id = auth.uid() and p.role = 'admin'
  );
$$;

-- 헬퍼: 현재 유저가 해당 책에 접근 가능한가 (소유 학생 또는 담당 교사 또는 admin)
create or replace function can_access_book(b_id uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select is_admin() or exists (
    select 1 from books b
    left join classrooms c on c.id = b.classroom_id
    where b.id = b_id
      and (b.student_id = auth.uid() or c.teacher_id = auth.uid())
  );
$$;

-- profiles: 본인 행만 읽기/수정. admin 전체.
create policy profiles_self_select on profiles for select
  using (id = auth.uid() or is_admin());
create policy profiles_self_upsert on profiles for insert
  with check (id = auth.uid());
create policy profiles_self_update on profiles for update
  using (id = auth.uid()) with check (id = auth.uid());

-- schools: 인증 유저 읽기. 쓰기는 admin.
create policy schools_read on schools for select using (auth.uid() is not null);
create policy schools_admin_write on schools for all
  using (is_admin()) with check (is_admin());

-- classrooms: 담당 교사 + 소속 학생 읽기. 교사가 자기 학급 생성/수정. admin 전체.
create policy classrooms_member_select on classrooms for select using (
  is_admin()
  or teacher_id = auth.uid()
  or exists (select 1 from enrollments e where e.classroom_id = id and e.student_id = auth.uid())
);
create policy classrooms_teacher_write on classrooms for all
  using (teacher_id = auth.uid() or is_admin())
  with check (teacher_id = auth.uid() or is_admin());

-- enrollments: 본인 등록 + 담당 교사 + admin.
create policy enrollments_select on enrollments for select using (
  is_admin()
  or student_id = auth.uid()
  or exists (select 1 from classrooms c where c.id = classroom_id and c.teacher_id = auth.uid())
);
create policy enrollments_student_join on enrollments for insert
  with check (student_id = auth.uid());

-- prompts: 학급 멤버(교사/학생) 읽기. 담당 교사 쓰기.
create policy prompts_member_select on prompts for select using (
  is_admin()
  or exists (select 1 from classrooms c where c.id = classroom_id
             and (c.teacher_id = auth.uid()
                  or exists (select 1 from enrollments e where e.classroom_id = c.id and e.student_id = auth.uid())))
);
create policy prompts_teacher_write on prompts for all
  using (exists (select 1 from classrooms c where c.id = classroom_id and (c.teacher_id = auth.uid() or is_admin())))
  with check (exists (select 1 from classrooms c where c.id = classroom_id and (c.teacher_id = auth.uid() or is_admin())));

-- books: 소유 학생 + 담당 교사 + admin.
create policy books_access_select on books for select using (can_access_book(id));
create policy books_student_insert on books for insert with check (student_id = auth.uid());
create policy books_student_update on books for update
  using (student_id = auth.uid() or is_admin()) with check (student_id = auth.uid() or is_admin());

-- bibles / chapters / plan_messages / chapter_chunks / learning_artifacts: 책 접근 권한을 따른다.
create policy bibles_access on bibles for all
  using (can_access_book(book_id)) with check (can_access_book(book_id));
create policy chapters_access on chapters for all
  using (can_access_book(book_id)) with check (can_access_book(book_id));
create policy plan_messages_access on plan_messages for all
  using (can_access_book(book_id)) with check (can_access_book(book_id));
create policy chapter_chunks_access on chapter_chunks for all
  using (can_access_book(book_id)) with check (can_access_book(book_id));
create policy learning_artifacts_access on learning_artifacts for all
  using (can_access_book(book_id)) with check (can_access_book(book_id));

-- events: 본인 책 쓰기/읽기 + 담당 교사/ admin 읽기.
create policy events_access on events for all
  using (can_access_book(book_id)) with check (can_access_book(book_id));

-- safety_flags: 담당 교사/admin 읽기. 시스템(서비스 롤)이 생성.
create policy safety_flags_select on safety_flags for select using (can_access_book(book_id));
