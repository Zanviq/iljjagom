# 일짜곰 Backend

Python **FastAPI** 기반 백엔드. AI 집필 파이프라인과 데이터/인증을 담당한다.

## 기술 스택
- FastAPI (Python), SSE 비동기 스트리밍
- Supabase (PostgreSQL + pgvector) — Bible/임베딩 저장, 인증, 스토리지
- Google Gemini 2.5 (Pro/Flash/Flash-Lite), Imagen 4
- 인증: Supabase Auth + Google OAuth

## 역할
- 4계층 AI 파이프라인(설계·집필·편집·대화) + 이미지 생성 오케스트레이션
- Bible(단일 진실 원천) 관리, RAG 검색(pgvector)
- 교사 발제(학습 목표) → 사건 분배·검증
- RLS 기반 학급/학교 단위 데이터 격리

> 상세 설계: `documents/for-claude/planning-designing/` (내부 문서)

_초기 스캐폴드 단계입니다._
