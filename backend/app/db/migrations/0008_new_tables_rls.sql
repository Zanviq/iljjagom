-- 일짜곰 스키마 0008 — 신규 테이블 RLS (0002 패턴 계승)
-- 쓰기(insert)는 서비스 롤(백엔드)이 담당 — 유저 토큰 경로 insert 정책은 두지 않아 시스템만 생성.
-- (0002 의 safety_flags 와 동일 철학)

alter table ai_sessions   enable row level security;
alter table ai_steps      enable row level security;
alter table messages      enable row level security;
alter table token_usage   enable row level security;
alter table notifications enable row level security;
alter table app_settings  enable row level security;
alter table audit_log     enable row level security;

-- 책 단위 산출물: can_access_book() 재사용 (소유 학생/담당 교사/admin)
drop policy if exists ai_sessions_access on ai_sessions;
create policy ai_sessions_access on ai_sessions for select using (can_access_book(book_id));

drop policy if exists messages_access on messages;
create policy messages_access on messages for select using (can_access_book(book_id));

-- ai_steps / token_usage: 세션의 book 권한을 따른다(조인)
drop policy if exists ai_steps_access on ai_steps;
create policy ai_steps_access on ai_steps for select using (
  exists (select 1 from ai_sessions s where s.id = session_id and can_access_book(s.book_id))
);

drop policy if exists token_usage_access on token_usage;
create policy token_usage_access on token_usage for select using (
  is_admin()
  or exists (select 1 from ai_sessions s where s.id = session_id and can_access_book(s.book_id))
);

-- 관리자 전용
drop policy if exists app_settings_admin on app_settings;
create policy app_settings_admin on app_settings for all using (is_admin()) with check (is_admin());

drop policy if exists audit_log_admin on audit_log;
create policy audit_log_admin on audit_log for select using (is_admin());

-- 알림: 본인 대상/역할 대상/브로드캐스트 읽기
drop policy if exists notifications_select on notifications;
create policy notifications_select on notifications for select using (
  is_admin()
  or target_user_id = auth.uid()
  or is_broadcast
  or (target_role is not null
      and exists (select 1 from profiles p where p.id = auth.uid() and p.role = target_role))
);

-- read_at 갱신(본인/admin). WITH CHECK 을 USING 과 동일하게 묶어 재타게팅(target 변경)을 차단.
drop policy if exists notifications_read_update on notifications;
create policy notifications_read_update on notifications for update
  using (target_user_id = auth.uid() or is_admin())
  with check (target_user_id = auth.uid() or is_admin());
