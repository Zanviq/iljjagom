"""FastAPI 앱 진입점 — 라우터 등록, CORS, 예외 핸들러."""
from __future__ import annotations

import asyncio

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()

    # 보안: 운영 신호(JWT 시크릿 또는 Supabase URL=실 토큰 검증 경로)가 있는데
    # 개발 인증이 켜져 있으면 기동 거부(설정 실수 차단, fail-closed).
    if settings.dev_auth and (settings.supabase_jwt_secret or settings.supabase_url):
        raise RuntimeError(
            "DEV_AUTH 가 켜진 상태로 SUPABASE_JWT_SECRET/SUPABASE_URL 이 설정되어 있습니다. "
            "운영 환경에서는 DEV_AUTH=false 로 두세요."
        )

    # 영속화: 운영(APP_ENV=prod)에서 Supabase 자격이 없으면 기동 거부(fail-closed).
    # 인메모리/Noop 폴백이 운영에 새지 않도록 한다(03-추가기능/01 §3.1).
    if settings.is_prod and not settings.use_supabase:
        raise RuntimeError(
            "APP_ENV=prod 인데 Supabase 자격(SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)이 없습니다. "
            "운영에서는 인메모리 폴백이 금지됩니다."
        )
    app = FastAPI(
        title="일짜곰 백엔드",
        version="0.1.0",
        description="아이가 직접 만드는 어린이 도서 플랫폼 — P1 골격",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        """라이브니스 — 항상 빠르게 응답(외부 의존 없음). 호스팅 헬스체크용.

        운영(prod)인데 인메모리/mock 로 떨어지면 status=degraded 로 표기(경보 가시화).
        """
        storage = "supabase" if settings.use_supabase else "in-memory"
        ai = "google" if settings.use_real_ai else "mock"
        degraded = settings.is_prod and (storage != "supabase" or ai != "google")
        return {
            "status": "degraded" if degraded else "ok",
            "version": app.version,
            "env": settings.app_env,
            "storage": storage,
            "ai": ai,
        }

    @app.get("/health/ready", tags=["meta"])
    async def health_ready(response: Response) -> dict:
        """레디니스 — Supabase 연결을 가벼운 쿼리로 1회 확인. 실패 시 503."""
        from app.store import get_store

        db_ok = True
        if settings.use_supabase:
            try:
                # app_settings 단일 행 조회(가벼운 ping).
                await asyncio.to_thread(get_store().get_setting, "safety_level")
            except Exception:
                db_ok = False
        checks = {"db": db_ok, "ai_key": settings.use_real_ai}
        ready = db_ok
        if not ready:
            response.status_code = 503
        return {
            "status": "ok" if ready else "unavailable",
            "version": app.version,
            "env": settings.app_env,
            "checks": checks,
        }

    # 라우터 등록 (단계별로 추가)
    from app.api import admin, ai, auth, books, chapters, planning, safety, teacher

    app.include_router(auth.router)
    app.include_router(teacher.router)
    app.include_router(books.router)
    app.include_router(planning.router)
    app.include_router(chapters.router)
    app.include_router(admin.router)
    app.include_router(ai.router)
    app.include_router(safety.router)

    return app


app = create_app()
