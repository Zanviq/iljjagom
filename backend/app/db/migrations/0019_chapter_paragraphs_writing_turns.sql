-- 학생/15 §2: 자유집필 협업 — 좌 본문(문단)·우 대화(턴).
-- chapters.body 는 문단 재조립 캐시로 유지(독서/RAG/학습 하위호환). 협업 화면만 문단/턴을 사용.
create table if not exists public.chapter_paragraphs (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  book_id    uuid not null references public.books(id) on delete cascade,
  seq        int  not null,
  body       text not null,
  source     text not null default 'collab' check (source in ('collab', 'ai', 'revise')),
  created_at timestamptz not null default now(),
  unique (chapter_id, seq)
);

create table if not exists public.writing_turns (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  book_id    uuid not null references public.books(id) on delete cascade,
  role       text not null check (role in ('student', 'writer')),
  kind       text not null default 'message' check (kind in ('message', 'question', 'coaching')),
  content    text not null,
  paragraph_id uuid references public.chapter_paragraphs(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists chapter_paragraphs_chapter_idx on public.chapter_paragraphs(chapter_id, seq);
create index if not exists writing_turns_chapter_idx on public.writing_turns(chapter_id, created_at);

alter table public.chapter_paragraphs enable row level security;
alter table public.writing_turns enable row level security;

create policy chapter_paragraphs_access on public.chapter_paragraphs for all
  using (can_access_book(book_id)) with check (can_access_book(book_id));
create policy writing_turns_access on public.writing_turns for all
  using (can_access_book(book_id)) with check (can_access_book(book_id));
