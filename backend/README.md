# 일짜곰 Backend

Python **FastAPI** 기반 백엔드입니다. AI 집필 파이프라인과 데이터·인증을 담당합니다.

## 기술 스택
- FastAPI (Python), SSE 비동기 스트리밍
- Supabase (PostgreSQL + pgvector) — Bible/임베딩 저장, 인증, 스토리지
- Google Gemini 2.5 (Pro/Flash/Flash-Lite), Imagen 4
- 인증: Supabase Auth + Google OAuth (서버는 JWT 검증)

## 역할
- 4계층 AI 파이프라인(설계·집필·편집·대화) + 이미지 생성 오케스트레이션을 수행합니다.
- Bible(단일 진실 원천)을 관리하고, RAG 검색(pgvector)으로 호출당 토큰을 일정하게 유지합니다.
- 교사 발제(학습 목표)를 챕터별 사건으로 분배·검증합니다.
- RLS 기반으로 학급/학교 단위 데이터를 격리합니다.

## 디렉터리
```
app/
├─ main.py          # FastAPI 앱, 라우터/CORS/예외 핸들러
├─ config.py        # 환경설정 (Supabase/Google 키 없으면 인메모리·mock 폴백)
├─ deps.py          # 인증(현재 유저)·역할 가드·저장소 의존성
├─ errors.py        # 공통 에러 규약 (code/message/detail)
├─ api/             # 라우터: auth, teacher, books, planning, chapters
├─ ai/              # gemini, designer, writer, editor, chat, quiz, rag, imagen, safety
├─ services/        # 비즈니스 로직 + 접근제어(RLS 등가)
├─ store/           # Store 추상화 → InMemoryStore / SupabaseStore
├─ models/          # Pydantic 스키마 (응답은 camelCase)
└─ db/migrations/   # SQL: 테이블 + RLS + pgvector HNSW + match_chunks RPC
```

## 실행
```bash
# 1) 가상환경 + 설치
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"   # Windows
# source .venv/bin/activate && pip install -e ".[dev]"  # macOS/Linux

# 2) 환경변수
cp .env.example .env   # 키가 없어도 동작 (인메모리 저장소 + mock AI)

# 3) 개발 서버 (코드 변경 자동 반영은 app/ 만 감시)
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000

# 4) 테스트
.venv/Scripts/python.exe -m pytest
```

> `--reload` 만 쓰면 backend/ 전체를 감시하므로, 로그 파일을 `backend/` 안에 쓰거나 임시 스크립트를
> 두면 매번 재기동(reload storm)되어 요청이 끊깁니다. **`--reload-dir app`** 로 app/ 만 감시하고,
> 로그 파일은 backend/ 밖(또는 무시 경로)에 두세요.

키 없이 실행하면 `/health` 가 `{"storage":"in-memory","ai":"mock"}` 를 반환하며, API/SSE 계약이
결정적 mock 응답으로 그대로 동작합니다.

## 인증 (개발)
`.env` 의 `DEV_AUTH=true`(코드 기본값은 false) 일 때, 토큰을 `Authorization: Bearer dev:<email>:<role>`
형식으로 보내면 Supabase 없이 로그인 흐름을 검증할 수 있습니다. 운영에서는 `DEV_AUTH=false` + Supabase JWT 를 씁니다.
보안상 `SUPABASE_JWT_SECRET` 이 설정되어 있으면 dev 토큰은 무시되고(fail-closed) 앱 기동도 거부됩니다.

## 실키 모드 (Supabase + Gemini/Imagen)
`.env` 에 `SUPABASE_SERVICE_ROLE_KEY`·`SUPABASE_JWT_SECRET`(+선택 `GOOGLE_API_KEY`)를 채우고 `DEV_AUTH=false` 로 둡니다.
`/health` 가 `{"storage":"supabase","ai":"google"}` 로 바뀌고, 인증은 Supabase JWT(HS256) 만 허용합니다.
- 임베딩: `gemini-embedding-001` 기본 출력이 3072차원이라 `output_dimensionality=768` 로 줄여 DB 스키마(`vector(768)`, HNSW)와 맞춥니다.
- 삽화: 실키 시 Imagen 생성 → Supabase Storage `illustrations`(public) 업로드 → 공개 URL 을 반환합니다.
- 외부 AI 일시 오류(503/429)는 짧은 백오프로 재시도하고, 회복 불가 시 안전 폴백(placeholder/부분 결과)으로 강등합니다.

## 더 보기
상세 아키텍처·API·데이터 모델·운영 문서는 저장소 종합 문서 **[`documents/instructions/`](../documents/instructions/README.md)** 에 있습니다.
