# SSE / 실시간

> 집필 본문은 Server-Sent Events로 글자 단위 스트리밍한다. 생성 대기(수십 초) 중에도 화면이 멈추지 않게 하기 위함. 자유집필 협업·총괄 AI는 동기 응답(POST)이다.

## 1. 집필 스트림
`GET /books/{id}/chapters/{n}/stream` — `Content-Type: text/event-stream`.

클라이언트는 `EventSource` 대신 **fetch + ReadableStream**으로 받는다(Authorization 헤더 전달 위해). `lib/sse.ts`가 파싱한다.

### 이벤트
| event | data(JSON) | 의미 |
| --- | --- | --- |
| `meta` | `{ chapterIdx, mode:"free\|guided", totalChaptersPlanned }` | 시작 메타. `mode`로 렌더 분기 |
| `illustration` | `{ url, alt }` | 삽화(유도모드는 본문보다 먼저) |
| `prompt` | `{ text }` | 유도모드 능동 질문 |
| `token` | `{ text }` | 본문 조각(append) |
| `done` | `{ chapterIdx, words[], nextChapterAvailable, charCount }` | 챕터 종료 |
| `error` | `{ code, message, retryable, retryAfter? }` | 오류 |

하트비트(`: ping`)로 연결을 유지한다.

### 유도모드 삽화 선노출
`mode==="guided"` 챕터는 **삽화 + 능동 질문을 먼저** 보여주고 본문을 가린다. 들어오는 `token`은 화면 뒤에서 버퍼링만 하다가, 아이가 "이야기 읽어볼까요?"를 탭하면 본문을 공개해 글자 단위로 흐른다("보고 → 생각 → 읽기"). 자유모드(`free`)는 `meta` 수신 즉시 스트리밍한다.

### 재연결 (`?from=`)
끊기면 마지막 오프셋부터 재요청한다: `GET .../stream?from=<charOffset>`. 오프셋은 **UTF-16 길이**로 프론트/백이 일치(한글 정합). `error.retryable`이면 백오프 후 재시도하고, `done` 미수신 정상 종료 시에도 재시도해 누락을 막는다. 본문 지연 자체는 백그라운드 선생성으로 줄여 끊김을 예방한다.

### 저장본 우선
이미 생성·저장된 챕터(`body`가 차 있음)는 재생성 없이 **저장본을 즉시 스트리밍**한다. 수정요청(`revise`) 완료 후 재구독하면 수정 반영된 저장본이 흐른다. 다음 장은 현재 장을 읽는 동안 백그라운드로 미리 생성되어 진입 시 대기가 없다.

## 2. 자유집필 협업 (동기 POST)
기·승 챕터는 SSE가 아니라 한 마디=한 문단 동기 응답이다.
`POST /books/{id}/chapters/{n}/collab`
- 요청: `{ message, accept? }` (`accept`=직전 AI 지도 제안 수용 여부)
- 응답 `CollabReply`:
```json
{ "kind": "paragraph",
  "paragraph": { "seq": 2, "body": "토끼는 처음엔 떨었지만…" },
  "question": "이제 다음엔 무슨 일이 생길까?",
  "chapterComplete": false }
```
또는 지도:
```json
{ "kind": "coaching",
  "coaching": { "text": "물론 그것도 좋지! 근데 이건 어때?…", "reasons": ["흐름","주제"] },
  "chapterComplete": false }
```
새로고침 복원은 `GET .../collab` → `{ paragraphs[], turns[], chapterComplete }`. (자세히: `05-작동흐름/02-자유집필-협업.md`)

## 3. 총괄 AI (동기 POST)
`POST /ai/overseer/messages` → `{ sessionId, reply, actions:[{type:"navigate",to,label,auto?}] }`. 프론트는 `reply`를 표시하고 `actions`를 버튼으로 렌더(클릭 시 `router.push(to)`).

## 4. 실시간 갱신(폴링)
관리자 콘솔의 실시간 상태·알림은 `app_settings.notify_interval_sec`(기본 180초) 주기로 재조회한다(필요 시 SSE로 격상).
