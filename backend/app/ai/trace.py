"""AI 흐름 트레이스 헬퍼 — 기존 절차에 ai_session/ai_steps/token_usage 를 비침습적으로 더한다.

설계: 03-추가기능/02 §4·§6(관측 연계). 기존 4계층을 전면 ReAct 로 바꾸지 않고도
"어떤 역할이 어떤 스킬을 어떤 순서로 했는지"를 관리자 페이지가 볼 수 있게 한다.

원칙: 트레이스 기록 실패는 사용자 흐름을 절대 막지 않는다(모든 작업 try/except).
"""
from __future__ import annotations

from typing import Any

from app.ai.gemini import GeminiClient
from app.ai.skills.base import Budget, SkillContext
from app.config import Settings
from app.store.base import Store
from app.util import now_iso


class Trace:
    """단일 AI 흐름(설계/집필/편집/수정)의 세션 + 스텝 기록기."""

    def __init__(
        self,
        store: Store,
        gemini: GeminiClient,
        settings: Settings,
        role: str,
        book_id: str | None = None,
        model: str | None = None,
    ) -> None:
        self.store = store
        self.role = role
        self.model = model
        self.session = None
        self.ctx: SkillContext | None = None
        try:
            self.session = store.create_ai_session(book_id, role, model)
            self.ctx = SkillContext(
                store=store,
                gemini=gemini,
                settings=settings,
                session_id=self.session.id,
                book_id=book_id,
                budget=Budget(max_steps=64),
            )
        except Exception:
            self.session = None
            self.ctx = None

    @property
    def session_id(self) -> str | None:
        return self.session.id if self.session else None

    def step(
        self,
        thought: str | None,
        skill: str,
        args: dict[str, Any],
        observation: dict[str, Any],
        model: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        ms: int | None = None,
    ) -> None:
        if not self.ctx:
            return
        try:
            if tokens_in or tokens_out:
                self.ctx.log_tokens(model or self.model or self.role, tokens_in, tokens_out)
            self.ctx.emit(thought, skill, args, observation, ms=ms)
        except Exception:
            pass

    def end(
        self, status: str = "done", summary: str | None = None, error: str | None = None
    ) -> None:
        if not self.session:
            return
        try:
            self.store.update_ai_session(
                self.session.id,
                status=status,
                summary=summary,
                error=error,
                ended_at=now_iso(),
            )
        except Exception:
            pass
