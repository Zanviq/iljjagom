"""공유 타입 베이스 — 03-기능명세서 §7.

응답은 camelCase 로 직렬화하고, 요청은 camelCase/snake_case 모두 허용한다.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
