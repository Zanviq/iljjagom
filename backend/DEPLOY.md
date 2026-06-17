# 일짜곰 백엔드 배포 가이드

> 현재는 **즉시 배포 가능한 상태만 준비**(실제 배포는 보류). 무상태(stateless)·컨테이너·환경변수 분리 완료.
> 설계 근거: `documents/for-claude/planning-designing/03-추가기능/01-supabase-영속화-및-배포준비.md` §4·§5.

## 1. 실행 모드 (APP_ENV)

| 값 | 동작 |
| --- | --- |
| `prod` | Supabase 자격(`SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`)이 없으면 **기동 거부**(fail-closed). 인메모리/Noop 폴백 금지. |
| `dev` | 자격 없으면 인메모리 폴백(경고 로그, 영속화 안 됨). |
| `test` | 항상 인메모리 허용(`conftest` 가 자동 설정). |

운영 배포는 `APP_ENV=prod` + `DEV_AUTH=false` 필수.

## 2. 환경변수

| 변수 | 운영 필수 | 용도 |
| --- | --- | --- |
| `SUPABASE_URL` | ✅ | DB/Auth/Storage |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | 서버 전용(RLS 우회). 클라이언트 노출 금지 |
| `SUPABASE_JWT_SECRET` | 선택 | 레거시 HS256 토큰 검증(ES256/JWKS 가 기본) |
| `GOOGLE_API_KEY` | ✅(권장) | Gemini/Imagen. 비면 mock(운영 부적합) |
| `ADMIN_EMAILS` | ✅ | 관리자 화이트리스트(쉼표 구분) |
| `ALLOWED_ORIGINS` | ✅ | CORS. 배포 프론트 도메인 추가(쉼표 구분) |
| `APP_ENV` | ✅ | `prod` |
| `DEV_AUTH` | ✅ | `false` |
| `PORT` | 배포 | 컨테이너 포트(호스팅이 주입, 기본 8000) |
| `WEB_CONCURRENCY` | 선택 | uvicorn 워커 수(무상태 전제, 기본 2) |
| `REDIS_URL` | 선택 | rate limit 확장(미설정 시 DB 기반) |
| `GEMINI_MODEL_*`·`IMAGEN_MODEL`·`GEMINI_EMBED_MODEL` | 선택 | 모델 기본값(런타임은 `app_settings.models` 우선) |

> **비밀은 환경변수/플랫폼 시크릿 스토어에만.** 저장소·문서·`app_settings`(DB) 어디에도 키 값 금지. 설정 패널은 "키 존재 여부"만 노출.

## 3. 헬스체크

- `GET /health` — 라이브니스(항상 빠름, 외부 의존 없음). `{status, version, env, storage, ai}`. 운영인데 인메모리/mock 면 `status:"degraded"`.
- `GET /health/ready` — 레디니스(Supabase 가벼운 쿼리 1회). `{status, checks:{db, ai_key}}`. DB 실패 시 **503**.
- 호스팅 헬스체크 경로는 `/health`(빠름) 권장.

## 4. 컨테이너

```bash
# 빌드
docker build -t iljjagom-backend ./backend
# 로컬 기동(.env 주입)
docker run --rm -p 8000:8000 --env-file backend/.env iljjagom-backend
# 확인
curl localhost:8000/health
```
- `backend/Dockerfile`(python:3.12-slim, 무상태, `--workers`), `backend/.dockerignore`(`.env`·`tests`·캐시 제외).
- 운영은 `--reload` 금지(이미 Dockerfile CMD 에 없음).

## 5. 호스팅 (택1, 모두 always-on 필요 — 알림 백그라운드 가동 전제)

- **Render**: Web Service · Docker · Health Check Path `/health` · env 에 §2 변수. `PORT` 자동 주입. 상시 가동은 유료 플랜.
- **Fly.io**: `fly.toml`(internal_port 8000, `[checks] /health`) · `fly secrets set` 으로 비밀 · 글로벌 엣지.
- **Railway**: Dockerfile 자동 감지 · `PORT` 주입 · Variables 탭에 env.

배포 후 백엔드 `ALLOWED_ORIGINS` 에 프론트 도메인(Vercel) 추가 → 재기동.

## 6. 프론트(Vercel)

- env: `NEXT_PUBLIC_API_BASE_URL`(배포 백엔드 URL), `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- `next build` 통과 확인. 배포 도메인을 백엔드 CORS 에 등록.

## 7. 마이그레이션 적용

- 스키마 파일: `backend/app/db/migrations/0001~0011*.sql` (멱등 — `if not exists`/enum 가드/`on conflict do nothing`).
- 적용: Supabase CLI(`supabase db push` 또는 `migration up`) 또는 대시보드 SQL Editor 에 순서대로 실행.
- **앱 기동 전에 마이그레이션 적용**(코드와 스키마 버전 일치). `0004` 는 결번(클라우드에는 match_chunks 패치로 존재).
- 신규 테이블: ai_sessions·ai_steps·messages·token_usage·notifications·app_settings·audit_log·rate_hits(전부 RLS on, 쓰기는 서비스 롤).
