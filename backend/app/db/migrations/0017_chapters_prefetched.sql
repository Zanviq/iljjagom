-- 학생/06: 다음 장 백그라운드 선생성(prefetch) 표식.
-- 본문만 채워졌고 학생이 아직 진입하지 않은 챕터를 구분 → chaptersDone/대시보드 진척에서 제외.
-- 학생 진입(스트림) 시 false 로 풀린다.
alter table public.chapters
  add column if not exists prefetched boolean not null default false;
