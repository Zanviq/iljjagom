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


async def guided_prompt(
    gemini: GeminiClient, bible: dict, event: dict
) -> str:
    """유도 모드 능동질문 — 삽화/장면 기반으로 결말 비공개 질문 1개. (FR-S5, 05 §5.2)

    본문 토큰보다 먼저 던져 대기 시간을 채운다. 결말/줄거리는 절대 묻거나 드러내지 않는다.
    """
    summary = event.get("summary", "")
    if gemini.mock:
        # 결정적: 장면 요약 기반 1문장(결말 비공개).
        chars = bible.get("characters", [])
        who = chars[0].get("name", "주인공") if chars else "주인공"
        return f"{who}은(는) 지금 어떤 마음일까요? 그림 속 장면을 보고 상상해 볼까요?"

    prompt = (
        f"{_INTERVIEWER_SYSTEM}\n"
        "다음 장면의 삽화를 보고, 어린 독자가 상상하며 답할 수 있는 질문 한 문장을 만든다. "
        "이야기의 결말이나 앞으로의 줄거리는 절대 묻지도 드러내지도 않는다.\n"
        f"이번 장면: {summary}\n\n능동 질문 한 문장:"
    )
    text = await gemini.generate_text(gemini.settings.gemini_model_flash_lite, prompt)
    return text.strip() or "이 그림 속에서는 무슨 일이 벌어지고 있을까요?"


async def persona_reply(
    gemini: GeminiClient, character_name: str, traits: list[str], letter_body: str
) -> str:
    """인물 페르소나로 학생 편지에 답장한다(FR-S11). 결말/줄거리는 절대 누설하지 않는다."""
    if gemini.mock:
        return (
            f"안녕, 나는 {character_name}이야. 너의 편지를 받아서 정말 기뻤어! "
            "너의 마음이 따뜻하게 느껴졌어. 우리 이야기의 다음 장면도 함께 기대해 보자. 고마워!"
        )

    trait_line = ", ".join(traits) if traits else "다정한"
    prompt = (
        f"너는 어린이 동화 속 인물 '{character_name}'({trait_line} 성격)이다. "
        "어린 독자가 너에게 쓴 편지에 그 인물의 말투로 다정하게 답장한다. "
        "이야기의 결말이나 앞으로의 줄거리는 절대 말하지 않는다. "
        "초등학생이 읽기 쉬운 한국어로 서너 문장만 쓴다.\n"
        f"독자의 편지: {letter_body}\n\n{character_name}의 답장:"
    )
    return (await gemini.generate_text(gemini.settings.gemini_model_flash_lite, prompt)).strip()


async def interpret_revision(gemini: GeminiClient, instruction: str) -> str:
    """학생의 자유로운 수정 요청을 집필 AI 가 쓸 한 줄 지시문으로 정리한다(FR-S6).

    결말 변경/비밀 누설 요구는 그대로 전달하지 않고 장면 묘사 수준으로 좁힌다.
    """
    cleaned = " ".join(instruction.split()).strip()
    if gemini.mock:
        return cleaned

    prompt = (
        "너는 어린이 동화 편집 보조다. 아래는 독자(어린이)가 한 챕터에 대해 말한 수정 요청이다. "
        "이를 작가가 실행할 수 있는 간결한 한 문장 지시로 바꿔라. "
        "이야기의 결말을 바꾸거나 미리 드러내는 요구는 '이 장면을 더 생생하게' 수준으로 순화한다.\n"
        f"수정 요청: {cleaned}\n\n한 문장 지시:"
    )
    return (await gemini.generate_text(gemini.settings.gemini_model_flash_lite, prompt)).strip()
