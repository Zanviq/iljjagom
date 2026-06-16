"""FastAPI 앱 진입점 — 라우터 등록, CORS, 예외 핸들러."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()
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
        return {
            "status": "ok",
            "storage": "supabase" if settings.use_supabase else "in-memory",
            "ai": "google" if settings.use_real_ai else "mock",
        }

    # 라우터 등록 (단계별로 추가)
    from app.api import auth, books, chapters, planning, teacher

    app.include_router(auth.router)
    app.include_router(teacher.router)
    app.include_router(books.router)
    app.include_router(planning.router)
    app.include_router(chapters.router)

    return app


app = create_app()
