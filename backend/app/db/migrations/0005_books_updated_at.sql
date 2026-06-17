-- 일짜곰 스키마 0005 — books.updated_at
-- GET /books(내 책 목록/이어 읽기)의 updatedAt + 최근 활동 순 정렬용.
-- 책 생성/상태전이/챕터 집필 완료 시 앱(또는 update)이 갱신한다.

alter table books
  add column if not exists updated_at timestamptz not null default now();

create index if not exists books_student_updated_idx
  on books (student_id, updated_at desc);
