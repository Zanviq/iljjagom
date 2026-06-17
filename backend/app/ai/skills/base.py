"""Skill 기반 — Skill 추상, SkillContext(트레이스/토큰/예산), run_skill 헬퍼.

설계: 03-추가기능/02-ai-skills-및-react-루프.md §3.2.
- 능력 1개 = 파일 1개. `skills/__init__.py` 가 자동 수집(SKILLS).
- 모든 스킬 실행은 run_skill 을 거쳐 ai_steps 에 기록되고, LLM 호출은 token_usage 에 기록된다.
- mock 모드에서 결정적으로 동작(테스트 그린).
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.ai.gemini import GeminiClient
from app.config import Settings
from app.store.base import Store


def estimate_tokens(text: str) -> int:
    """대략 토큰 수(관측용). 실 usage_metadata 대신 길이 기반 추정(약 4자=1토큰)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class Budget:
    """ReAct/스킬 실행의 토큰·스텝 상한(00 §4 budget)."""

    max_steps: int = 8
    max_tokens: int = 200_000
    steps_used: int = 0
    tokens_used: int = 0

    def remaining_steps(self) -> int:
        return max(0, self.max_steps - self.steps_used)

    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.tokens_used)

    def exhausted(self) -> bool:
        return self.steps_used >= self.max_steps or self.tokens_used >= self.max_tokens


@dataclass
class SkillContext:
    """스킬 실행 컨텍스트 — 저장소·모델·세션·예산. emit/log_tokens 로 트레이스 기록."""

    store: Store
    gemini: GeminiClient
    settings: Settings
    session_id: str | None = None
    book_id: str | None = None
    user_id: str | None = None
    budget: Budget = field(default_factory=Budget)
    _step_idx: int = 0
    _last_tokens: tuple[int, int] = (0, 0)

    def model_for(self, role: str) -> str:
        """역할별 모델 — app_settings.models 우선, 없으면 settings 기본값."""
        models: dict[str, Any] = {}
        try:
            models = self.store.get_setting("models") or {}
        except Exception:
            models = {}
        if not isinstance(models, dict):
            models = {}
        defaults = {
            "designer": self.settings.gemini_model_pro,
            "writer": self.settings.gemini_model_flash,
            "editor": self.settings.gemini_model_flash,
            "chat": self.settings.gemini_model_flash_lite,
            "embed": self.settings.gemini_embed_model,
            "imagen": self.settings.imagen_model,
        }
        return models.get(role) or defaults.get(role) or self.settings.gemini_model_flash

    def log_tokens(self, model: str, tokens_in: int, tokens_out: int, est_cost: float = 0.0) -> None:
        self.budget.tokens_used += tokens_in + tokens_out
        self._last_tokens = (tokens_in, tokens_out)
        if self.session_id:
            try:
                self.store.add_token_usage(self.session_id, model, tokens_in, tokens_out, est_cost)
            except Exception:
                pass

    def emit(
        self,
        thought: str | None,
        skill: str,
        args: dict[str, Any],
        observation: dict[str, Any],
        ms: int | None = None,
    ) -> None:
        idx = self._step_idx
        self._step_idx += 1
        self.budget.steps_used += 1
        tin, tout = self._last_tokens
        if self.session_id:
            try:
                self.store.add_ai_step(
                    self.session_id, idx, thought, skill, args, observation, tin, tout, ms
                )
            except Exception:
                pass


class Skill(ABC):
    """능력 단위. name/description 은 ReAct 프롬프트에 노출, input_schema 로 args 검증."""

    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = {}
    danger: bool = False  # 외부효과(쓰기/외부호출) 여부 — 관측·안전검사 표시용

    @abstractmethod
    async def run(self, ctx: SkillContext, **args: Any) -> dict[str, Any]:
        """observation(JSON 직렬화 가능 dict) 반환."""
        ...


class SkillError(Exception):
    """스킬 args 검증/실행 오류."""


def validate_args(skill: Skill, args: dict[str, Any]) -> None:
    """input_schema(간이 JSON Schema: required + properties.type)로 args 검증."""
    schema = skill.input_schema or {}
    required = schema.get("required", [])
    for key in required:
        if key not in args or args[key] is None:
            raise SkillError(f"스킬 '{skill.name}' 필수 인자 누락: {key}")
    props = schema.get("properties", {})
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    for key, value in args.items():
        spec = props.get(key)
        if not spec:
            continue
        expected = type_map.get(spec.get("type"))
        if expected and value is not None and not isinstance(value, expected):
            raise SkillError(f"스킬 '{skill.name}' 인자 '{key}' 타입 불일치({spec.get('type')})")


async def run_skill(
    ctx: SkillContext, name: str, args: dict[str, Any], thought: str | None = None
) -> dict[str, Any]:
    """스킬을 검증·실행하고 ai_steps 에 1스텝 기록. observation 반환."""
    from app.ai.skills import SKILLS

    skill = SKILLS.get(name)
    if skill is None:
        raise SkillError(f"알 수 없는 스킬: {name}")
    validate_args(skill, args)
    ctx._last_tokens = (0, 0)
    t0 = time.monotonic()
    obs = await skill.run(ctx, **args)
    ms = int((time.monotonic() - t0) * 1000)
    ctx.emit(thought, name, args, obs, ms=ms)
    return obs
