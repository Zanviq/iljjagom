"""Tier4 대화 AI (Gemini Flash-Lite) — 기획 인터뷰어 / 유도질문 / 페르소나.

핵심 규칙(FR-S2): 인터뷰어는 결말/줄거리를 절대 발설하지 않는다.
mock 모드에서도 결말을 만들지 않고 인물·배경·분위기 질문만 한다.
"""
from __future__ import annotations

from app.ai.gemini import GeminiClient
from app.models.schemas import CharacterDraft, PlanReply

# 인터뷰어가 던질 수 있는 질문(화이트리스트) — 결말/줄거리 비공개.
_INTERVIEW_QUESTIONS = [
    "그 주인공은 어떤 성격을 가지고 있을까요?",
    "이야기는 어디에서 펼쳐지면 좋을까요?",
    "주인공 곁에는 누가 함께 있나요?",
    "이야기의 분위기는 밝았으면 좋겠어요, 신비로웠으면 좋겠어요?",
    "주인공이 가장 좋아하는 것은 무엇일까요?",
]

_READY_THRESHOLD = 3  # 학생 메시지가 이만큼 쌓이면 집필 시작 가능

_INTERVIEWER_SYSTEM = (
    "너는 어린이 작가를 돕는 다정한 인터뷰어다. "
    "인물·배경·분위기를 묻는 질문만 한다. "
    "이야기의 결말이나 앞으로의 줄거리는 절대 말하지 않는다. "
    "초등학생이 이해할 쉬운 한국어로 한두 문장만 답한다."
)

# 간단한 형용사 사전(mock 인물 특성 추출).
_TRAIT_WORDS = {
    "용감": "용감함",
    "씩씩": "씩씩함",
    "착한": "착함",
    "똑똑": "똑똑함",
    "친절": "친절함",
    "호기심": "호기심 많음",
    "장난": "장난스러움",
}


def _extract_draft(student_messages: list[str]) -> CharacterDraft:
    traits: list[str] = []
    name: str | None = None
    for msg in student_messages:
        for key, label in _TRAIT_WORDS.items():
            if key in msg and label not in traits:
                traits.append(label)
        # "이름은 OO" / "OO(이)라고 해" 같은 단순 패턴은 P1에선 생략하고 traits 위주.
    return CharacterDraft(name=name, traits=traits)


async def interview_reply(
    gemini: GeminiClient, student_messages: list[str], latest: str
) -> PlanReply:
    draft = _extract_draft(student_messages)
    ready = len(student_messages) >= _READY_THRESHOLD

    if gemini.mock:
        idx = (len(student_messages) - 1) % len(_INTERVIEW_QUESTIONS)
        reply = _INTERVIEW_QUESTIONS[idx]
        if ready:
            reply = "좋아요, 멋진 인물이 만들어졌어요! 이제 이야기를 시작해 볼까요?"
        return PlanReply(reply=reply, character_draft=draft, ready_to_write=ready)

    history = "\n".join(f"- {m}" for m in student_messages)
    prompt = (
        f"{_INTERVIEWER_SYSTEM}\n\n지금까지 학생이 말한 것:\n{history}\n\n"
        f"학생의 마지막 말: {latest}\n\n인터뷰어의 다음 한 마디:"
    )
    reply = await gemini.generate_text(gemini.settings.gemini_model_flash_lite, prompt)
    return PlanReply(reply=reply.strip(), character_draft=draft, ready_to_write=ready)
