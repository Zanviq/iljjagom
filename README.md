# 일짜곰 (iljjagom)

<!-- 배너 이미지: documents/screenshots/banner.png 로 저장하면 표시됩니다(없으면 생략 가능). -->
<!-- ![일짜곰](documents/screenshots/banner.png) -->

> 아이가 직접 이야기를 만들고, AI가 결말을 비밀로 펼치며, 교사가 학급 단위로 학습 목표를 발제해 교과 수업에 쓰는 **어린이 도서 플랫폼**입니다.

핵심 가설은 단순합니다 — **내가 만든 이야기라서 결말이 궁금해 끝까지 읽고, 읽으면서 배운다.**

- **대상**: 유치원~초등 학생(주 사용자), 학급 교사, 운영 관리자
- **환경**: 웹 (1인 1태블릿 교실 + 가정)
- **1차 방향**: 일반 초등학생 독서 동기 회복 (다문화 한국어 교육은 확장 영역)

---

## 무엇이 특별한가

1. **자유 집필 → 유도 집필** — 기·승 단계는 아이가 AI와 한 문단씩 함께 쓰고(작가), 전·결 단계는 AI가 결말을 비밀로 한 챕터씩 펼칩니다(첫 독자). 전환은 매끄럽습니다.
2. **교사 발제 개별화** — 교사가 학습 목표를 내면 학급 30명이 *각자 다른 이야기*로 *같은 목표*를 거칩니다.
3. **본문·삽화 동시 생성** — 유도 모드는 삽화를 먼저 보여 호기심을 자극하고, 본문은 글자 단위로 흐릅니다.
4. **읽기 = 배움** — 완독하면 낱말·퀴즈·감정 곡선·인물 편지·독후감으로 이어집니다.

---

## 화면 미리보기

> 아래 이미지는 `documents/screenshots/` 폴더의 파일을 불러옵니다. 아직 이미지를 넣지 않았다면
> 깨진 링크로 보일 수 있으며, 캡처를 **표에 적힌 파일명 그대로** 그 폴더에 저장하면 표시됩니다.
> 각 화면이 무엇을 담아야 하는지는 [`documents/screenshots/README.md`](documents/screenshots/README.md) 를 참고하세요.

### 학생

| 홈(내 책장) | 기획 대화 |
| --- | --- |
| ![학생 홈](documents/screenshots/student-01-home.png) | ![기획 대화](documents/screenshots/student-02-plan.png) |
| **자유집필 협업(기·승)** | **중간활동(퀴즈)** |
| ![자유집필 협업](documents/screenshots/student-03-collab.png) | ![중간활동](documents/screenshots/student-04-mid-activity.png) |
| **전·결 읽기(삽화+본문)** | **학습 활동(낱말·퀴즈·감정·편지)** |
| ![전결 읽기](documents/screenshots/student-05-read.png) | ![학습 활동](documents/screenshots/student-06-learn.png) |

### 교사

| 학급 목록 | 발제 만들기 |
| --- | --- |
| ![학급 목록](documents/screenshots/teacher-01-classes.png) | ![발제 만들기](documents/screenshots/teacher-02-prompt.png) |
| **대시보드(정량 지표)** | **학생 작업 열람** |
| ![대시보드](documents/screenshots/teacher-03-dashboard.png) | ![학생 작업 열람](documents/screenshots/teacher-04-student-work.png) |

### 관리자

| 관리자 콘솔 |
| --- |
| ![관리자 콘솔](documents/screenshots/admin-01-console.png) |

---

## 기술 스택

| 영역 | 선택 |
| --- | --- |
| 프론트엔드 | Next.js 16 (App Router) · TypeScript · Tailwind v4 · @supabase/ssr |
| 백엔드 | Python FastAPI (SSE 비동기) |
| 데이터베이스 | Supabase (PostgreSQL + pgvector) · Storage · RLS |
| 인증 | Google OAuth (Supabase Auth, ES256 JWKS 검증) |
| AI | Google Gemini 2.5 (Pro/Flash/Flash-Lite) · Imagen 4 |

---

## 저장소 구조

```
iljjagom/
├─ backend/        # FastAPI — AI 파이프라인·데이터·인증 (자세히: backend/README.md)
├─ frontend/       # Next.js 16 웹 (자세히: frontend/README.md)
└─ documents/
   ├─ instructions/  # 📚 프로젝트 종합 문서 (개요·아키텍처·기능·API·흐름·디자인·운영)
   └─ screenshots/   # README 화면 미리보기 이미지 (파일명 규칙: screenshots/README.md)
```

---

## 빠른 시작

```bash
# 백엔드 (터미널 1) — http://localhost:8000
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"   # Windows
cp .env.example .env                                   # 키 없이도 동작(인메모리+mock)
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000

# 프론트엔드 (터미널 2) — http://localhost:3000
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

키 없이 실행하면 인메모리 저장소 + 결정적 mock AI로 전체 흐름이 동작합니다. 실 서비스는 Supabase·Google 키를 채웁니다(→ `documents/instructions/07-운영/01-실행-배포.md`).

---

## 문서

프로젝트의 모든 상세 문서는 **[`documents/instructions/`](documents/instructions/README.md)** 에 있습니다 — 서비스 개요, 아키텍처, 역할별 기능, API 레퍼런스, 작동 흐름, 디자인 시스템, 운영/배포. 무엇이 어디 있는지는 [instructions/README.md](documents/instructions/README.md) 를 참고하세요.

---

_국민대학교 · 일짜곰 팀 · 2026_
