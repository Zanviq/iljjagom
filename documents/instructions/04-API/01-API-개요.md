# API 개요

일짜곰 백엔드 API의 공통 규약을 정의한다. 모든 엔드포인트의 상세는 `02-API-레퍼런스.md`, 실시간 스트림(SSE)·협업은 `03-SSE-실시간.md`를 참조한다.

---

## 1. Base URL

| 환경 | Base URL |
| --- | --- |
| 로컬 개발 | `http://localhost:8000` |
| 운영 | 배포 도메인(환경변수 `NEXT_PUBLIC_API_BASE_URL`) |

- 프론트엔드는 `NEXT_PUBLIC_API_BASE_URL` 로 베이스 주소를 주입받는다.
- 모든 경로는 이 베이스 뒤에 붙는다. 예: `GET {BASE}/me`.

---

## 2. 인증

모든 보호 엔드포인트는 `Authorization` 헤더에 Supabase 사용자 JWT(액세스 토큰)를 담아 호출한다.

```http
Authorization: Bearer <Supabase JWT>
```

- **검증 방식**: Supabase 사용자 JWT를 **ES256(비대칭, JWKS)** 로 검증한다.
  - JWKS: `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`
  - 발급자 `iss = {SUPABASE_URL}/auth/v1`, 대상 `aud = authenticated`, 만료(`exp`)를 확인한다.
  - 레거시 **HS256**(`SUPABASE_JWT_SECRET`) 토큰도 과도기 호환한다.
- 토큰이 없거나 만료되면 `401 unauthorized` 를 반환한다.
- 역할(`student` / `teacher` / `admin`)에 맞지 않는 엔드포인트 접근은 `403 forbidden` 이다.
- 데이터 격리는 **Supabase RLS**로 DB 차원에서 강제된다(서버 책임). 토큰 안에 들어 있는 사용자/역할만 자기 범위의 데이터를 읽고 쓸 수 있다.
- 관리자는 `ADMIN_EMAILS` 화이트리스트 + `profiles.role='admin'` 으로 판별한다.

### 보호자 동의 게이트

미성년 보호를 위해, **보호자 미동의 학생**이 AI 자유 텍스트 기능(기획 대화·집필 협업·수정 요청·편지·총괄 AI 등)을 호출하면 `403 consent_required` 를 반환한다. 동의 상태는 `GET /me` 의 `guardianConsent` 로 확인한다.

---

## 3. 콘텐츠 타입

| 종류 | Content-Type |
| --- | --- |
| 일반 요청/응답 | `application/json` |
| 실시간 스트림(집필 SSE) | `text/event-stream` |

요청 바디는 JSON(`application/json`)으로 보낸다.

---

## 4. 응답 표기 규약 (camelCase)

- 응답 바디의 **모든 필드는 camelCase** 다(예: `classId`, `createdAt`, `chaptersDone`).
- 요청 바디도 camelCase 를 사용한다.
- 백엔드 내부는 snake_case(Pydantic)이지만 직렬화 시 camelCase 별칭으로 변환된다. 클라이언트는 camelCase 만 다룬다.

---

## 5. 시간 / ID / 페이지네이션 규약

| 항목 | 규약 |
| --- | --- |
| 시간 | ISO-8601 **UTC** 문자열(예: `2026-06-19T08:30:00Z`). 필드명은 `createdAt`·`updatedAt`·`startedAt`·`endedAt`·`reviewedAt` 등. |
| ID | **UUID** 문자열. `id`·`bookId`·`classId`·`promptId`·`sessionId` 등. |
| 페이지네이션 | 목록 엔드포인트는 쿼리 `limit`(상한 있음, 예: 1~200) + 필요 시 기간 필터 `from`·`to`(ISO-8601)를 받는다. 별도 커서/오프셋 페이지네이션은 사용하지 않으며, 목록은 보통 최근순으로 반환된다. |
| 정렬 | 별도 명시가 없으면 최근 활동/생성 순(내림차순). 예: `GET /books` 는 `updatedAt` 내림차순. |

---

## 6. 공통 에러 규약

오류 응답 바디는 항상 다음 형태다.

```json
{ "error": { "code": "STRING_CODE", "message": "사람이 읽는 설명", "detail": {} } }
```

- `code`: 기계 판별용 문자열 코드(아래 표).
- `message`: 사용자/개발자에게 보여 줄 한국어 설명.
- `detail`: 선택. 추가 컨텍스트(예: 검증 실패 필드, 재시도 제안 등).

### HTTP 상태 / 코드 표

| HTTP | code | 의미 |
| --- | --- | --- |
| 400 | `validation_error` | 요청 검증 실패(필수값 누락·형식 오류·안전 게이트 위반 등) |
| 401 | `unauthorized` | 토큰 없음/만료/검증 실패 |
| 403 | `forbidden` | 권한 없음(역할 불일치/RLS 범위 밖) |
| 403 | `consent_required` | 보호자 미동의 학생의 AI 자유 텍스트 기능 차단 |
| 404 | `not_found` | 리소스 없음 |
| 409 | `conflict` | 상태 충돌(예: 이미 집필 중, 집필 전 챕터 수정, 마지막 관리자 강등, 중간활동 미완료) |
| 429 | `rate_limited` | 호출/비용 한도 초과 |
| 500 | `internal_error` | 서버 오류 |
| 503 | `ai_unavailable` | AI 제공자 오류/타임아웃 |

---

## 7. Rate Limit (429 `rate_limited`)

비용·과호출 방지를 위해 **사용자별 60초 윈도** 호출 한도가 적용된다. 한도를 넘으면 `429 rate_limited` 를 반환한다.

| 버킷 | 한도(/60s) | 대상 |
| --- | --- | --- |
| `plan` | 60 | `POST /books/{id}/plan/messages` (기획 대화) |
| `design` | 10 | `POST /books/{id}/design` |
| `revise` | 20 | `POST /books/{id}/chapters/{idx}/revise` |
| `collab` | 60 | `POST /books/{id}/chapters/{idx}/collab` (협업) |
| `letters` | 20 | `POST /books/{id}/letters` |
| `learning` | 30 | `GET /books/{id}/learning` |
| `events` | 120 | `POST /events` (배치) |
| `learning-results` | 30 | `POST /books/{id}/learning-results` |
| `overseer` | 60 | `POST /ai/overseer/messages` (총괄 AI) |
| `board` | 30 | `POST /books/{id}/board-posts` |
| `rotate-code` | (낮음) | `POST /classes/{id}/rotate-code` |

- **읽기 스트림**(집필 SSE)은 저장본 재제공·재구독 구조라 한도가 없다.
- 한도값은 런타임 설정(`app_settings.rate_limits`)에서 조정될 수 있으며(관리자), 미설정 시 위 기본값을 따른다. 카운터는 `rate_hits` 테이블에 저장되어 멀티 워커에서도 정합한다.
- 프론트엔드는 `429` 수신 시 잠시 후 재시도를 안내한다.

---

## 8. 헬스 체크

| 엔드포인트 | 용도 |
| --- | --- |
| `GET /health` | 라이브니스. `version`·`env`·`storage`·`ai`·`status`(degraded 가능) 반환. |
| `GET /health/ready` | 레디니스. Supabase 핑 등 `{checks:{db,ai_key}}`, 실패 시 `503`. |

헬스 체크는 인증이 필요 없다.
