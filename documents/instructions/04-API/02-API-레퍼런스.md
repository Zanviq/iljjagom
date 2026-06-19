# API 레퍼런스

> 정본 계약은 `documents/for-claude/planning-designing/02-제작문서-초안/03-기능명세서.md`. 모든 보호 엔드포인트는 `Authorization: Bearer <Supabase JWT>`. 응답은 camelCase. 공통 규약은 [01-API-개요](01-API-개요.md) 참고.

표기: 역할 = 호출 가능 역할. 요청/응답은 요지(주요 필드).

## 인증 / 계정
| 메서드·경로 | 역할 | 요청 → 응답 |
| --- | --- | --- |
| `GET /me` | 전체 | → `{ id, email, role, grade, guardianConsent, needsOnboarding, classId, className, name }` |
| `POST /onboarding` | 신규 | `{ role:"student\|teacher", classCode?, guardianConsent }` → `/me` 형태 |
| `GET /health` · `/health/ready` | 공개 | 라이브/레디니스. `{storage, ai}` 모드 |

## 학급 / 발제 (교사)
| 메서드·경로 | 역할 | 요청 → 응답 |
| --- | --- | --- |
| `GET /classes` | 교사 | → `{ classes:[{ id, name, schoolId, studentCount, code }] }` |
| `POST /classes` · `PATCH /classes/{id}` | 교사 | 학급 생성/수정·코드 재발급 |
| `GET·PUT /classes/{id}/settings` | 교사 | 학급 설정(안전강도·기능 토글) |
| `POST /classes/{id}/prompts` | 교사 | `{ topic, learningObjectives[], assessment, language }` → 발제 |
| `GET /classes/{id}/prompts` | 학급원 | 발제 목록 |
| `GET /classes/{id}/prompts/{pid}/submissions` | 교사 | 발제별 학생·책·작성내용 집계 |
| `GET /classes/{id}/dashboard` | 교사 | `{ students:[{ studentId, bookId, status, chaptersDone, totalChapters }], summary:{ studentCount, booksStarted, booksDone, completionRate, vocabCount, … } }` |

## 책 / 기획 / 설계 (학생)
| 메서드·경로 | 역할 | 요청 → 응답 |
| --- | --- | --- |
| `POST /books` | 학생 | `{ promptId }` → `{ id, status:"planning", … }` |
| `GET /books` | 학생 | 내 책 목록 → `{ books:[{ id, title, status, chaptersDone, totalChaptersPlanned, updatedAt }] }` |
| `GET /books/{id}` | 접근자 | `{ status, title, chapters:[{ idx, mode, reviewStatus, hasIllustration, paragraphCount }], totalChaptersPlanned }` |
| `POST /books/{id}/plan/messages` | 학생 | `{ message }` → `{ reply, characterDraft, readyToWrite, interviewClosed }` |
| `POST /books/{id}/design` | 학생 | → `{ status:"designing\|done", totalChaptersPlanned }` (백그라운드 선생성으로 즉시화) |

## 집필 / 협업 (학생)
| 메서드·경로 | 역할 | 요청 → 응답 |
| --- | --- | --- |
| `GET /books/{id}/chapters/{n}/stream` | 학생 | **SSE** 집필 스트림 → [03-SSE-실시간](03-SSE-실시간.md) |
| `POST /books/{id}/chapters/{n}/collab` | 학생 | (free 전용) `{ message, accept? }` → `CollabReply{ kind:"paragraph\|coaching", paragraph?, coaching?, question?, chapterComplete }`. guided면 409 |
| `GET /books/{id}/chapters/{n}/collab` | 접근자 | 협업 복원 → `{ paragraphs[], turns[], chapterComplete }` |
| `POST /books/{id}/chapters/{n}/revise` | 학생 | `{ instruction }` → 202 (재구독으로 반영) |
| `GET /books/{id}/words?term=` | 학생 | 단어 도움 → `{ term, reading, meaning }` |

## 중간활동 (학생)
| 메서드·경로 | 역할 | 동작 |
| --- | --- | --- |
| `GET /books/{id}/mid-activity` | 학생 | 기·승 완료 후 중간 퀴즈/독후감 |
| `POST /books/{id}/mid-activity/complete` | 학생 | 완료 처리(필수) → 전·결 진입 해제. 미완료 시 전·결 진입 conflict |

## 학습 활동 (학생)
| 메서드·경로 | 역할 | 응답/동작 |
| --- | --- | --- |
| `GET /books/{id}/learning` | 학생 | `{ vocab[], quiz[], essayBlanks[], emotion(입력 틀: labels+points), letterCharacters:[{id,name,traits}] }` |
| `POST·GET /books/{id}/learning-results` | 학생 | 퀴즈/독후감/감정곡선 결과 저장·조회 |
| `POST /books/{id}/letters` | 학생 | `{ to(인물 선택), body }` → `{ status:"answered\|held", reply? }` |
| `GET /books/{id}/letters` | 학생 | 내 편지·상태 |

## 게시판 / 발표
| 메서드·경로 | 역할 | 동작 |
| --- | --- | --- |
| `POST /books/{id}/board-posts` | 학생 | 완성 책 발표 등록(소속 학급·`status=done` 검증) |
| `GET /classes/{id}/board-posts` | 학급원 | 게시판 목록(학생=published, 교사=전체) |
| `GET /board-posts/{id}` | 접근자 | 발표 상세(스냅샷) |
| `POST /board-posts/{id}/approve\|reject` | 교사 | 승인/반려 |

## 안전 (교사/관리자)
| 메서드·경로 | 역할 | 동작 |
| --- | --- | --- |
| `GET /classes/{id}/safety-flags` · `GET /safety-flags/{id}` · `POST /safety-flags/{id}/resolve` | 교사/관리자 | 안전 신호 검토·종결 |
| `GET /classes/{id}/letters` · `POST /letters/{id}/approve\|reject` | 교사 | 보류 편지 검토 |
| `GET /admin/safety-flags` | 관리자 | 전역 안전 신호 |

## 측정 (학생)
| 메서드·경로 | 동작 |
| --- | --- |
| `POST /events` | 행동 로그 배치(챕터 열람·체류·단어터치·완독·재방문 등) |

## 총괄 AI / AI 세션
| 메서드·경로 | 역할 | 동작 |
| --- | --- | --- |
| `POST /ai/overseer/messages` | 학생 | `{ message, sessionId?, route? }` → `{ sessionId, reply, actions:[{type:"navigate",to,label,auto?}] }` |
| `GET /ai/sessions` · `GET /ai/sessions/{id}` | 관리자 | ReAct 세션·스텝(프롬프트·관측·토큰 동봉) |
| `POST /ai/sessions/{id}/answer` | 관련자 | ask_user 일시정지 재개 `{ choice\|text }` |

## 관리자 콘솔
| 메서드·경로 | 동작 |
| --- | --- |
| `GET /admin/usage` · `GET /admin/usage/tokens?groupBy=` | 사용량·토큰/비용 집계 |
| `GET /admin/users` · `PATCH /admin/users/{id}` · `POST /admin/users/{id}/deactivate` | 사용자·역할·비활성 |
| `GET /admin/users/{id}/overview` · `GET /admin/books/{id}/timeline` | 드릴다운(책·단계 타임라인) |
| `GET /admin/messages` | 대화 검색 |
| `GET·PUT /admin/settings` | 런타임 설정(선택형 enum, 시크릿 비노출) |
| `GET /admin/notifications` · `POST /admin/notifications` · `POST /notifications/{id}/read` | 알림 |
| `POST /admin/backup/export\|import` | 백업/복원 |

모든 신규 계약은 `03-기능명세서` → `handoff/api-changes.md`에 먼저 정의된 뒤 구현된다.
