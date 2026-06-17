-- 일짜곰 스키마 0003 — 인덱스
-- pgvector HNSW(cosine) + 조회 경로 인덱스.

-- 임베딩 ANN 검색 (코사인). gemini-embedding-001 = 768차원.
create index if not exists chapter_chunks_embedding_hnsw
  on chapter_chunks using hnsw (embedding vector_cosine_ops);

create index if not exists chapter_chunks_book_idx on chapter_chunks (book_id);
create index if not exists books_classroom_idx on books (classroom_id);
create index if not exists books_student_idx on books (student_id);
create index if not exists chapters_book_idx_idx on chapters (book_id, idx);
create index if not exists prompts_classroom_idx on prompts (classroom_id);
create index if not exists plan_messages_book_idx on plan_messages (book_id, created_at);

-- RAG 인출용 RPC: 책 범위 코사인 ANN. 백엔드 SupabaseStore.search_chunks 가 호출.
create or replace function match_chunks(
  p_book_id uuid,
  p_query vector(768),
  p_k int default 5
)
returns table (id uuid, book_id uuid, chapter_id uuid, content text, similarity float)
language sql stable set search_path = public as $$
  select cc.id, cc.book_id, cc.chapter_id, cc.content,
         1 - (cc.embedding <=> p_query) as similarity
  from chapter_chunks cc
  where cc.book_id = p_book_id and cc.embedding is not null
  order by cc.embedding <=> p_query
  limit p_k;
$$;
