"""테스트 공통 픽스처 — 인메모리 저장소 + mock AI + 개발 토큰."""
from __future__ import annotations

import os

# 테스트는 .env(실키)와 무관하게 항상 인메모리 + mock + dev 인증으로 격리한다.
# (os.environ 이 .env 파일보다 우선하므로 실키가 채워져 있어도 빈 값으로 덮는다.)
os.environ["DEV_AUTH"] = "true"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
os.environ["SUPABASE_JWT_SECRET"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ.setdefault("ADMIN_EMAILS", "admin@iljjagom.test")

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app
from app.store import get_store


@pytest.fixture(autouse=True)
def _reset_state():
    # lru_cache 된 store/settings + 호출 한도 를 테스트마다 초기화.
    from app.ratelimit import reset as reset_ratelimit

    get_store.cache_clear()
    get_settings.cache_clear()
    reset_ratelimit()
    yield
    get_store.cache_clear()
    reset_ratelimit()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def auth(email: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer dev:{email}:{role}"}
