"""Tier4 대화 AI (Gemini Flash-Lite) — 기획 인터뷰어 / 유도질문 / 페르소나.

핵심 규칙(FR-S2): 인터뷰어는 결말/줄거리를 절대 발설하지 않는다.
mock 모드에서도 결말을 만들지 않고 인물·배경·분위기 질문만 한다.
"""
from __future__ import annotations

from app.ai.brief import bible_brief
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

# readyToWrite 충족 후: 새 질문 금지, 공감/칭찬 한 문장만(학생/03).
_INTERVIEWER_SYSTEM_READY = (
    "너는 어린이 작가를 돕는 다정한 인터뷰어다. "
    "이미 이야기를 시작할 준비가 끝났다. 새로운 질문은 절대 하지 않는다. "
    "학생이 방금 한 말에 공감하고 칭찬하는 한 문장만 답한다. "
    "물음표(?)나 '~할까요?', '어떤가요?' 같은 되묻는 말은 쓰지 않는다. "
    "이야기의 결말이나 줄거리는 말하지 않는다."
)


def _strip_trailing_question(text: str) -> str:
    """ready 안전망 — 끝에 붙은 질문절을 제거. 남는 게 없으면 칭찬 기본문."""
    t = (text or "").strip()
    if not t:
        return "와, 정말 멋진 이야기 준비가 됐어요!"
    # 문장 분리 후 물음표로 끝나는 마지막 문장을 잘라낸다.
    import re

    sentences = re.split(r"(?<=[.!?。])\s+", t)
    kept = [s for s in sentences if not s.rstrip().endswith("?")]
    result = " ".join(kept).strip()
    if not result:
        # 전부 질문이면 물음표 앞부분만 살리거나 기본 칭찬.
        result = t.split("?")[0].strip() or "와, 정말 멋진 이야기 준비가 됐어요!"
    return result

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
        if ready:
            reply = "와, 정말 멋진 인물이 만들어졌어요!"  # 질문 어미 없는 공감(학생/03)
        else:
            idx = (len(student_messages) - 1) % len(_INTERVIEW_QUESTIONS)
            reply = _INTERVIEW_QUESTIONS[idx]
        return PlanReply(
            reply=reply, character_draft=draft, ready_to_write=ready, interview_closed=ready
        )

    history = "\n".join(f"- {m}" for m in student_messages)
    system = _INTERVIEWER_SYSTEM_READY if ready else _INTERVIEWER_SYSTEM
    prompt = (
        f"{system}\n\n지금까지 학생이 말한 것:\n{history}\n\n"
        f"학생의 마지막 말: {latest}\n\n인터뷰어의 다음 한 마디:"
    )
    reply = await gemini.generate_text(gemini.settings.gemini_model_flash_lite, prompt)
    reply = _strip_trailing_question(reply.strip()) if ready else reply.strip()
    return PlanReply(
        reply=reply, character_draft=draft, ready_to_write=ready, interview_closed=ready
    )


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


def _content_tokens(text: str) -> set[str]:
    """본문 흐름 비교용 내용어 토큰(표제어 근사, 2자+ 한글)."""
    from app.ai.writer import _has_korean, _lemma

    out: set[str] = set()
    for raw in (text or "").replace("\n", " ").split(" "):
        tok = "".join(ch for ch in raw if ch.isalnum())
        lemma = _lemma(tok)
        if len(lemma) >= 2 and _has_korean(lemma):
            out.add(lemma)
    return out


def _coach_text(reasons: list[str], objective: str | None) -> str:
    """지도(coaching) 문구 — 학생 의도 긍정 + 대안 + 근거(사용자 원문 규약, 학생/15)."""
    bits = []
    if "흐름" in reasons:
        bits.append("앞 문단과 자연스럽게 이어지도록")
    if "주제" in reasons:
        bits.append(f"'{objective}' 주제가 잘 드러나도록" if objective else "이야기 주제가 잘 드러나도록")
    why = ", ".join(bits) or "이야기가 더 잘 이어지도록"
    return f"물론 그것도 좋아! 근데 {why} 살짝 바꿔보면 어떨까?"


async def assess_flow(
    gemini: GeminiClient, bible: dict, prev_paragraph: str, objective: str | None,
    student_intent: str,
) -> dict:
    """학생 의도가 (a)흐름(직전 문단과 자연스러운가)·(b)주제에 맞는지 판정(학생/15 §2.4).

    반환 `{action:'generate'|'coach', reasons:[...], suggestion:str|None}`.
    결말/secretArc 는 참조·노출하지 않는다(기·승 단계). 지도는 제안일 뿐 강제가 아니다.
    """
    if gemini.mock:
        # 결정적 휴리스틱: 첫 문단이거나 직전 문단과 공통 내용어가 있으면 흐름 OK → generate.
        if not (prev_paragraph or "").strip():
            return {"action": "generate", "reasons": [], "suggestion": None}
        if _content_tokens(prev_paragraph) & _content_tokens(student_intent):
            return {"action": "generate", "reasons": [], "suggestion": None}
        reasons = ["흐름"]
        return {"action": "coach", "reasons": reasons, "suggestion": _coach_text(reasons, objective)}

    obj_line = f"이번 장 학습 주제: {objective}\n" if objective else ""
    brief = bible_brief(bible)
    brief_block = f"{brief}\n" if brief else ""
    prompt = (
        "너는 어린이 작가를 돕는 다정한 글쓰기 코치다. 학생이 다음에 쓰고 싶다고 한 내용이 "
        "(a) 직전 문단과 자연스럽게 이어지는지 (b) 아래 [이야기 설정]의 인물·세계·주제에서 벗어나지 않는지 판단한다. "
        "이야기의 결말이나 앞으로의 줄거리는 절대 참조·언급하지 않는다. "
        "괜찮으면 그대로 진행하고, 어색하면 학생 의도를 먼저 긍정한 뒤 더 나은 방향을 근거와 함께 제안한다. "
        "반드시 아래 JSON 하나만 출력한다(설명·코드블록 금지).\n"
        '{"action":"generate|coach","reasons":["흐름"|"주제"],'
        '"suggestion":"coach 일 때 \'물론 그것도 좋아! 근데 …\' 한두 문장, generate 면 null"}\n\n'
        f"{brief_block}{obj_line}직전 문단: {prev_paragraph or '(아직 없음)'}\n학생이 쓰고 싶은 것: {student_intent}\n\nJSON:"
    )
    try:
        raw = await gemini.generate_text(gemini.settings.gemini_model_flash_lite, prompt)
        import json

        data = json.loads(_strip_json(raw))
        if isinstance(data, dict) and data.get("action") in ("generate", "coach"):
            data.setdefault("reasons", [])
            data.setdefault("suggestion", None)
            return data
    except Exception:
        pass
    # 파싱 실패 → 아동 주도성 존중: 생성으로 진행(폴백).
    return {"action": "generate", "reasons": [], "suggestion": None}


async def next_paragraph_question(
    gemini: GeminiClient, bible: dict, paragraphs_so_far: list[str],
    event: dict | None = None,
) -> str:
    """방금 쓴 문단 뒤 진행 질문 1개(학생/15 §2.4). 결말 비공개.

    이미 정해진 인물·세계(Bible 브리프)는 다시 묻지 않고 그 위에서 다음을 상상하게 한다(§01).
    """
    chars = bible.get("characters", [])
    who = chars[0].get("name", "주인공") if chars else "주인공"
    if gemini.mock:
        return f"좋아! 이제 {who}에게 다음엔 무슨 일이 생길까?"
    brief = bible_brief(bible, event)
    brief_block = f"{brief}\n" if brief else ""
    prompt = (
        f"{_INTERVIEWER_SYSTEM}\n"
        f"{brief_block}"
        "위 [이야기 설정]의 인물·세계는 이미 정해졌으니 다시 묻지 말고, 그 설정 위에서 "
        "지금까지 함께 쓴 이야기 뒤에 이어질 내용을 학생이 상상해 답할 수 있는 '진행 질문' 한 문장을 만든다. "
        "결말이나 앞으로의 줄거리는 절대 묻지도 드러내지도 않는다.\n"
        f"지금까지 문단:\n{chr(10).join(paragraphs_so_far[-3:]) or '(아직 없음)'}\n\n진행 질문 한 문장:"
    )
    text = await gemini.generate_text(gemini.settings.gemini_model_flash_lite, prompt)
    return text.strip() or f"이제 {who}에게 무슨 일이 생길까?"


def _strip_json(raw: str) -> str:
    t = (raw or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.endswith("```"):
            t = t[:-3]
        if t.startswith("json"):
            t = t[4:]
    t = t.strip()
    if not t.startswith("{"):
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1 and e > s:
            t = t[s : e + 1]
    return t


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
