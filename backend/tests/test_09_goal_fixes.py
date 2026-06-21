"""09 목표 수정 회귀 — 교사 장수 반영·이미지 종 강제·동적 인트로·페르소나·퀴즈 선생성."""
from __future__ import annotations

from app.ai import chat
from app.ai.gemini import GeminiClient
from app.config import get_settings
from app.deps import CurrentUser
from app.store import get_store
from app.store.records import PromptRecord


def _user(uid: str, role: str = "student") -> CurrentUser:
    return CurrentUser(id=uid, email=f"{uid}@x", role=role, profile=None, needs_onboarding=False)


class _FakeGemini:
    mock = False

    def __init__(self, payload: str = ""):
        self._payload = payload
        self.settings = get_settings()

    async def generate_text(self, model: str, prompt: str) -> str:
        self.last_prompt = prompt
        return self._payload


# --- #3/#5 교사 선택 장수: 기·승/전·결 절반 + 마지막 장 ---
async def test_designer_uses_teacher_chapter_count_mock():
    from app.ai.designer import build_bible

    prompt = PromptRecord(
        id="p", classroom_id="c", topic="물의 순환",
        learning_objectives=["증발", "응결"], assessment={}, chapters_planned=4,
    )
    bible = await build_bible(GeminiClient(), prompt, ["토끼 토토 이야기"], [])
    assert bible["totalChaptersPlanned"] == 4
    modes = [e["mode"] for e in sorted(bible["events"], key=lambda e: e["chapterIdx"])]
    assert modes == ["free", "free", "guided", "guided"]  # 4장 → 2자유 2유도


def test_designer_normalize_forces_requested_total():
    """LLM 이 다른 totalChaptersPlanned 를 내도 교사 선택 장수를 강제."""
    from app.ai.designer import _normalize_bible

    data = {"totalChaptersPlanned": 6, "events": [], "characters": []}
    norm = _normalize_bible(data, ["증발"], 4)
    assert norm["totalChaptersPlanned"] == 4
    assert len(norm["events"]) == 4


def test_resolve_total_default_when_unset():
    from app.ai.designer import DEFAULT_TOTAL_CHAPTERS, _resolve_total

    p = PromptRecord(id="p", classroom_id="c", topic="t", learning_objectives=[], assessment={})
    assert _resolve_total(p) == DEFAULT_TOTAL_CHAPTERS
    assert _resolve_total(None) == DEFAULT_TOTAL_CHAPTERS


# --- #6 이미지: 종 강제 + 다른 동물 금지 ---
def test_image_prompt_species_and_exclusivity():
    from app.ai.imagen import _build_image_prompt

    chars = [
        {"id": "a", "name": "토토", "species": "토끼", "appearance": "흰 털"},
        {"id": "b", "name": "개굴이", "species": "개구리", "appearance": "초록 피부"},
    ]
    p = _build_image_prompt("연못에서 노는 장면", chars)
    assert "토끼" in p and "개구리" in p  # 종 명시
    assert "오직" in p and "거북이" in p  # 목록 외 동물(예: 거북이) 금지
    assert "복제" in p  # 같은 인물 복제 금지


# --- #2 자유집필 인트로 동적화 ---
def test_collab_opening_question_dynamic():
    from app.services import collab

    store = get_store()
    book = store.create_book("kid-09c", None, None)
    store.upsert_bible(book.id, {
        "characters": [{"name": "토토"}, {"name": "개굴이"}],
        "events": [{"chapterIdx": 1, "mode": "free"}, {"chapterIdx": 2, "mode": "free"}],
    })
    q1 = collab._opening_question(store, book.id, 1)
    q2 = collab._opening_question(store, book.id, 2)
    assert "토토" in q1 and "토토" in q2  # 인물명 반영(고정 문구 아님)
    assert q1 != q2  # 장마다 다름
    assert "이어" in q2  # 2장은 1장과 단절되지 않게 '이어' 표현


# --- #9 편지 페르소나: bible·이야기 맥락 반영 ---
async def test_persona_reply_includes_story_context():
    fake = _FakeGemini("토토가 답장했어요!")
    reply = await chat.persona_reply(
        fake, "토토", ["호기심"], "토토야 안녕!",
        species="토끼", appearance="흰 털", world={"setting": "방울방울 산"},
        story_title="물의 순환", story_context="토토가 물웅덩이를 발견했어요.",
    )
    assert reply  # 실 응답 반환
    # 프롬프트에 종·배경·이야기 맥락·제목이 실제로 들어갔는지.
    assert "토끼" in fake.last_prompt
    assert "방울방울 산" in fake.last_prompt
    assert "물웅덩이를 발견" in fake.last_prompt
    assert "물의 순환" in fake.last_prompt
    assert "결말" in fake.last_prompt  # 결말 누설 금지 지시 포함


# --- #7 마무리 퀴즈 백그라운드 선생성 ---
async def test_prefetch_learning_caches_quiz():
    from app.services import learning

    store = get_store()
    book = store.create_book("kid-09p", None, None)
    store.upsert_bible(book.id, {
        "title": "물 이야기", "totalChaptersPlanned": 2,
        "characters": [{"name": "토토", "species": "토끼"}],
        "events": [{"chapterIdx": 1, "mode": "free", "objective": "증발"},
                   {"chapterIdx": 2, "mode": "guided", "objective": "응결"}],
    })
    for i in (1, 2):
        c = store.create_chapter(book.id, i, "free" if i == 1 else "guided")
        store.update_chapter(c.id, body=f"{i}장: 토토가 물을 찾는 이야기.", char_count=40)
    await learning.prefetch_learning(store, GeminiClient(), book.id)
    cached = store.list_learning_artifacts(book_id=book.id, type=learning.LEARNING_SET)
    assert len(cached) == 1  # 마무리 교재 캐시 생성됨
    assert cached[0].data.get("quiz")  # 퀴즈 포함
