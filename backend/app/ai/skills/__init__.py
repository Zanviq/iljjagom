"""Skill 레지스트리 — 패키지 내 모듈을 스캔해 Skill 구현을 자동 수집한다.

각 스킬 모듈은 Skill 하위 클래스를 1개 이상 정의한다(name 필수).
SKILLS: dict[name -> Skill 인스턴스].
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil

from app.ai.skills.base import (  # re-export
    Budget,
    Skill,
    SkillContext,
    SkillError,
    estimate_tokens,
    run_skill,
    validate_args,
)

__all__ = [
    "SKILLS",
    "Skill",
    "SkillContext",
    "Budget",
    "SkillError",
    "run_skill",
    "validate_args",
    "estimate_tokens",
    "skill_catalog",
]


def _discover() -> dict[str, Skill]:
    registry: dict[str, Skill] = {}
    for mod_info in pkgutil.iter_modules(__path__):
        if mod_info.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{mod_info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Skill)
                and obj is not Skill
                and obj.__module__ == module.__name__
                and getattr(obj, "name", "")
            ):
                instance = obj()
                registry[instance.name] = instance
    return registry


SKILLS: dict[str, Skill] = _discover()


def skill_catalog(names: list[str] | None = None) -> list[dict]:
    """ReAct 프롬프트용 스킬 스펙 목록(name·description·input_schema·danger)."""
    items = []
    for name, skill in SKILLS.items():
        if names is not None and name not in names:
            continue
        items.append(
            {
                "name": skill.name,
                "description": skill.description,
                "input_schema": skill.input_schema,
                "danger": skill.danger,
            }
        )
    return items
