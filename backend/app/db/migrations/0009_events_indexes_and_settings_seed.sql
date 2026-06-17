-- 일짜곰 스키마 0009 — events 인덱스 보강 + app_settings 기본 시드
-- 근거: 03-추가기능/00 §4·§6·§7, 01 §3.2(0009).
-- learning_results 는 신설하지 않고 기존 learning_artifacts 를 정본으로 채택(중복 방지).

-- events 집계용 인덱스(체류·토글·단어터치·완독)
create index if not exists events_book_idx on events(book_id, created_at);
create index if not exists events_student_idx on events(student_id, created_at);
create index if not exists events_type_idx on events(type, created_at);

-- app_settings 기본 시드 — 시크릿(키) 절대 저장 금지. 값은 런타임 조정 가능.
-- on conflict do nothing: 재실행 안전 + 관리자가 바꾼 값을 덮어쓰지 않음.
insert into app_settings (key, value) values
  ('models', '{
    "designer": "gemini-2.5-pro",
    "writer": "gemini-2.5-flash",
    "editor": "gemini-2.5-flash",
    "chat": "gemini-2.5-flash-lite",
    "embed": "gemini-embedding-001",
    "imagen": "imagen-4.0-generate-001"
  }'::jsonb),
  ('feature_toggles', '{
    "guided_mode": true,
    "illustrations": true,
    "letters": true
  }'::jsonb),
  ('rate_limits', '{
    "plan":    {"limit": 60, "window": 60},
    "design":  {"limit": 10, "window": 60},
    "revise":  {"limit": 20, "window": 60},
    "letters": {"limit": 20, "window": 60},
    "learning":{"limit": 30, "window": 60}
  }'::jsonb),
  ('notify_interval_sec', '180'::jsonb),
  ('safety_level', '"standard"'::jsonb)
on conflict (key) do nothing;
