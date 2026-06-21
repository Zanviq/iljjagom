# 일짜곰 Frontend

**Next.js 16 (App Router) + TypeScript** 기반 웹 프론트엔드입니다. 학교(태블릿 브라우저)와 가정 모두에서
쓸 수 있도록 웹에 최적화했습니다.

## 기술 스택
- Next.js 16 (App Router, React Server Components), React, TypeScript
- Tailwind CSS v4
- Supabase 클라이언트(@supabase/ssr) — 인증·세션
- SSE 로 AI 본문을 글자 단위로 스트리밍 수신

## 화면 구성
- **학생**: 홈(내 책장) → 기획 대화 → 자유집필 협업(기·승) → 중간활동 → 전·결 읽기(삽화 선노출) → 학습 활동(낱말·퀴즈·감정 곡선·인물 편지) → 학급 발표
- **교사**: 학급 관리·발제(주제·학습 목표·이야기 길이·AI 지도 강도), 대시보드(정량 지표), 학생 작업 열람, 안전 검토, 게시판 승인
- **관리자**: 운영 콘솔(지표·세션·사용량 등 모니터링)

## 디렉터리
```
frontend/
├─ app/             # App Router 라우트
│  ├─ (student)/    # 홈·기획·집필·읽기·학습
│  ├─ (teacher)/    # 학급·발제·대시보드·열람
│  ├─ (admin)/      # 운영 콘솔
│  └─ login/ · onboarding/
├─ components/      # reader·writing·planning·learning·teacher·ai·ui
├─ lib/             # api.ts·types.ts·sse.ts·auth/ 등 클라이언트 유틸
└─ proxy.ts         # 미들웨어(세션·접근 제어)
```

## 실행
```bash
# 1) 설치
npm install

# 2) 환경변수
cp .env.example .env.local

# 3) 개발 서버 — http://localhost:3000
npm run dev

# 4) 린트 / 빌드
npm run lint
npm run build
```

백엔드를 키 없이 실행하면(인메모리 + mock AI) 프론트도 전체 흐름을 그대로 따라갈 수 있습니다.
백엔드 주소는 `.env.local` 에서 지정합니다.

## 더 보기
화면 가이드·디자인 시스템·역할별 기능 등 상세 문서는 저장소 종합 문서
**[`documents/instructions/`](../documents/instructions/README.md)** 에 있습니다.
