-- 학생/07: 삽화 Storage 버킷 보장.
-- illustrations 버킷이 없으면 업로드가 조용히 실패 → placeholder(코드 글자)만 노출됐다.
-- public 버킷으로 생성(공개 URL 제공). 이미 있으면 public 으로 보정.
insert into storage.buckets (id, name, public)
values ('illustrations', 'illustrations', true)
on conflict (id) do update set public = true;
