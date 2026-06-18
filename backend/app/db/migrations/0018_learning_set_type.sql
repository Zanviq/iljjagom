-- 학생/13: 생성 학습교재 캐시(learning_set) + 중간활동(mid_activity, 학생/15 §3) 타입 허용.
-- 학생 자기보고 결과(quiz/essay/emotion/letter)와 구분되는 서버 캐시 행.
alter table public.learning_artifacts
  drop constraint if exists learning_artifacts_type_check;
alter table public.learning_artifacts
  add constraint learning_artifacts_type_check
  check (type in ('vocab', 'quiz', 'essay', 'letter', 'emotion', 'learning_set', 'mid_activity'));
