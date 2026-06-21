"""Imagen 4 삽화 생성 — 챕터마다 1장. Bible 인물 카드로 외형 일관성 유지.

실 모델 경로: Imagen 으로 이미지 생성 → Supabase Storage(illustrations 버킷) 업로드 → 공개 URL.
키가 없거나 실패하면 결정적 placeholder URL 로 안전 폴백한다(계약/SSE 흐름 불변).
"""
from __future__ import annotations

from app.ai.gemini import GeminiClient
from app.storage import get_storage

# 식별자 코드를 노출하지 않는 중립 폴백(학생/07). 실 삽화 실패/미설정 시 임시 표시.
# 프론트는 이 URL 패턴이면 스켈레톤/중립 표시로 대체할 수 있다(is_placeholder_url).
_PLACEHOLDER_PREFIX = "https://placehold.co/"
_PLACEHOLDER_URL = (
    "https://placehold.co/768x512/f5efe6/d9c7ad?text=%EA%B7%B8%EB%A6%BC+%EC%A4%80%EB%B9%84+%EC%A4%91"
)


def _placeholder() -> str:
    return _PLACEHOLDER_URL


def is_placeholder_url(url: str | None) -> bool:
    """placeholder(임시) URL 인지 — illustration_path 박제 방지·프론트 폴백 판단용."""
    return bool(url) and url.startswith(_PLACEHOLDER_PREFIX)


def _character_identity(c: dict) -> str:
    """인물 외형 고정 식별 문구 — 매 장 동일 텍스트(외형 일관, C5).

    종류(species)를 가장 먼저 박아 Imagen 이 엉뚱한 동물로 그리지 않게 한다(예: 토끼/개구리).
    appearance 가 구조화 dict({hair,eyes,outfit,distinctive,...})면 항목을 풀어 쓰고,
    문자열이면 그대로 사용한다. traits 도 덧붙여 인물 정체성을 강화한다.
    """
    name = c.get("name", "")
    species = c.get("species") or c.get("kind") or ""
    ap = c.get("appearance")
    if isinstance(ap, dict):
        parts = [ap.get(k) for k in ("hair", "eyes", "outfit", "ageLook", "distinctive")]
        desc = ", ".join(p for p in parts if p)
    else:
        desc = ap or ""
    traits = c.get("traits") or []
    trait_str = ", ".join(str(t) for t in traits[:3]) if isinstance(traits, list) else ""
    head = f"{name}({species})" if species else name
    tail = ", ".join(b for b in (desc, trait_str) if b)
    return f"{head} — {tail}" if tail else head


def _species_list(characters: list[dict]) -> str:
    """등장인물 종류 목록(예: '토끼, 개구리') — 다른 동물 등장 차단 문구에 쓴다."""
    seen: list[str] = []
    for c in characters:
        sp = c.get("species") or c.get("kind")
        if sp and sp not in seen:
            seen.append(str(sp))
    return ", ".join(seen)


def _build_image_prompt(summary: str, characters: list[dict]) -> str:
    # 인물 순서 안정화(id 기준) → 장마다 동일 입력. 과밀 방지로 상위 3명.
    ordered = sorted(characters, key=lambda c: str(c.get("id", c.get("name", ""))))
    shown = ordered[:3]
    who = "; ".join(_character_identity(c) for c in shown)
    species = _species_list(shown)
    # 종류가 명시된 경우, 그 동물/사람만 그리고 다른 종은 금지(거북이 등 환각·복제 방지).
    only_line = (
        f"이 장면에 등장하는 것은 오직 다음뿐이다: {species}. 목록에 없는 사람이나 동물(예: 거북이, "
        "강아지 등)은 절대 그리지 않는다. 같은 인물을 여러 마리로 복제하지 않는다(각 인물은 한 번만). "
        if species else
        "장면에는 위에 적은 등장인물만 그린다. 목록에 없는 인물·동물은 추가하지 않고, 같은 인물을 "
        "여러 번 복제하지 않는다. "
    )
    return (
        "어린이 동화책 삽화, 따뜻하고 부드러운 색감, 안전한 그림체. "
        "같은 인물은 항상 같은 종류·외형(머리·눈·복장·특징)으로 일관되게 그린다. "
        f"등장인물: {who}. "
        f"{only_line}"
        f"장면: {summary}. "
        # 글자 박힘 방지(이미지 안에 텍스트/영어/캡션 금지) — 한국어+영어로 강하게 지시.
        "그림 안에 글자·문자·단어·숫자·자막·말풍선·서명·워터마크를 절대 넣지 않는다. "
        "No text, no letters, no words, no captions, no writing, no watermark, no signature anywhere in the image."
    )


async def generate_illustration(
    gemini: GeminiClient, book_id: str, chapter_idx: int, summary: str, characters: list[dict]
) -> tuple[str, str]:
    """(url, alt) 반환."""
    alt = f"{chapter_idx}장 삽화: {summary[:40]}"

    if gemini.mock or not gemini.settings.use_real_ai:
        return _placeholder(), alt

    # 실 모델: Imagen 생성 → Storage 업로드. 어느 단계든 실패하면 placeholder.
    data = await gemini.generate_image(_build_image_prompt(summary, characters))
    if data:
        url = get_storage().upload_illustration(f"{book_id}/{chapter_idx}.png", data)
        if url:
            return url, alt
    return _placeholder(), alt
