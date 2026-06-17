-- 일짜곰 스키마 0010 — notifications UPDATE 정책 WITH CHECK 강화
-- 근거: 보안 어드바이저(rls_policy_always_true). WITH CHECK(true) → USING 과 동일 조건으로
-- 묶어 본인 알림의 재타게팅(target_user_id 변경)을 차단한다. (0008 파일에도 반영됨, 멱등)

drop policy if exists notifications_read_update on notifications;
create policy notifications_read_update on notifications for update
  using (target_user_id = auth.uid() or is_admin())
  with check (target_user_id = auth.uid() or is_admin());
