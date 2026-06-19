-- 선생님/02: 학급 범위 설정(class_settings) + 발제 옵션 확장.
create table if not exists public.class_settings (
  classroom_id uuid primary key references public.classrooms(id) on delete cascade,
  value        jsonb not null default '{}'::jsonb,   -- {safetyLevel, featureToggles:{...}, ...}
  updated_by   uuid references public.profiles(id) on delete set null,
  updated_at   timestamptz not null default now()
);
alter table public.class_settings enable row level security;
-- 담당 교사·admin 만(학생은 설정 메타 접근 불가).
create policy class_settings_teacher_all on public.class_settings for all
  using (is_admin() or exists (select 1 from public.classrooms c
                               where c.id = classroom_id and c.teacher_id = auth.uid()))
  with check (is_admin() or exists (select 1 from public.classrooms c
                                    where c.id = classroom_id and c.teacher_id = auth.uid()));

-- 발제 옵션(권장 학년·장수·마감·상태·발제별 안전강도 오버라이드).
alter table public.prompts
  add column if not exists grade_band int,
  add column if not exists chapters_planned int,
  add column if not exists due_at timestamptz,
  add column if not exists status text not null default 'open' check (status in ('open', 'closed')),
  add column if not exists safety_level text;
