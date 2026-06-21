"""Tier4 대화 AI (Gemini Flash-Lite) — 기획 인터뷰어 / 유도질문 / 페르소나.

핵심 규칙(FR-S2): 인터뷰어는 결말/줄거리를 절대 발설하지 않는다.
mock 모드에서도 결말을 만들지 않고 인물·배경·분위기 질문만 한다.
"""
from __future__ import annotations

import re

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
        chars = bible.get("characters", []) or []
        first = chars[0] if chars else None
        who = (first.get("name", "주인공") if isinstance(first, dict) else (str(first) if first else "주인공"))
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
    student_intent: str, coaching_level: str = "light",
) -> dict:
    """학생 의도가 (a)흐름(직전 문단과 자연스러운가)·(b)주제에 맞는지 판정(학생/15 §2.4).

    반환 `{action:'generate'|'coach', reasons:[...], suggestion:str|None}`.
    결말/secretArc 는 참조·노출하지 않는다(기·승 단계). 지도는 제안일 뿐 강제가 아니다.

    coaching_level(06 §5) 로 간섭 강도 조절:
    - off: 점검 생략(항상 generate).
    - light(기본): 흐름이 '명백히' 끊길 때만 coach. 주제 일탈은 아동 창의성으로 허용(간섭 완화).
    - standard: 흐름 + 주제 모두 점검(종전 동작).
    """
    if coaching_level == "off":
        return {"action": "generate", "reasons": [], "suggestion": None}
    check_topic = coaching_level == "standard"

    if gemini.mock:
        # 결정적 휴리스틱: 첫 문단이거나 직전 문단과 공통 내용어가 있으면 흐름 OK → generate.
        if not (prev_paragraph or "").strip():
            return {"action": "generate", "reasons": [], "suggestion": None}
        if _content_tokens(prev_paragraph) & _content_tokens(student_intent):
            return {"action": "generate", "reasons": [], "suggestion": None}
        # light/standard 모두 흐름 단절은 coach. (mock 은 주제 판정 안 함)
        reasons = ["흐름"]
        return {"action": "coach", "reasons": reasons, "suggestion": _coach_text(reasons, objective)}

    obj_line = f"이번 장 학습 주제: {objective}\n" if (objective and check_topic) else ""
    brief = bible_brief(bible)
    brief_block = f"{brief}\n" if brief else ""
    if check_topic:
        criteria = (
            "(a) 직전 문단과 자연스럽게 이어지는지 (b) 아래 [이야기 설정]의 인물·세계·주제에서 "
            "크게 벗어나지 않는지 판단한다. "
        )
        reasons_hint = '["흐름"|"주제"]'
    else:
        # light: 흐름만. 주제/창의성은 폭넓게 허용해 간섭을 줄인다.
        criteria = (
            "직전 문단과 '명백히' 이어지지 않아 이야기가 갑자기 끊길 때만 살짝 돕는다. "
            "엉뚱하거나 새로운 상상은 아이의 창의성이니 그대로 존중해 generate 한다. "
        )
        reasons_hint = '["흐름"]'
    prompt = (
        "너는 어린이 작가를 돕는 다정한 글쓰기 코치다. 학생이 다음에 쓰고 싶다고 한 내용이 "
        f"{criteria}"
        "되도록 generate 를 우선하고, 정말 어색할 때만 coach 한다. "
        "이야기의 결말이나 앞으로의 줄거리는 절대 참조·언급하지 않는다. "
        "coach 일 때는 학생 의도를 먼저 긍정한 뒤 더 나은 방향을 부드럽게 제안한다. "
        "반드시 아래 JSON 하나만 출력한다(설명·코드블록 금지).\n"
        '{"action":"generate|coach","reasons":' + reasons_hint + ","
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
            # light 모드에서 모델이 '주제' 이유를 내도 무시(흐름만 인정) — 간섭 완화 보장.
            if not check_topic and data.get("action") == "coach":
                rs = [r for r in (data.get("reasons") or []) if r == "흐름"]
                if not rs:
                    return {"action": "generate", "reasons": [], "suggestion": None}
                data["reasons"] = rs
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
    chars = bible.get("characters", []) or []
    first = chars[0] if chars else None
    who = (first.get("name", "주인공") if isinstance(first, dict) else (str(first) if first else "주인공"))
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


# 협업 문단 '대화 수정' 의도 감지(05-기능수정 §02). 추가 LLM 왕복 없이 휴리스틱.
_EDIT_KEYWORDS = ("고쳐", "고치", "수정", "바꿔", "바꾸", "다시 써", "다시써", "다시 쓰", "고쳐줘", "바꿔줘")
_LAST_REFS = ("마지막", "방금", "이거", "이 문단", "위 문단", "지금 문단", "그 문단")
_ORDINAL_WORDS = {
    "첫 번째": 1, "첫번째": 1, "처음": 1, "첫째": 1,
    "두 번째": 2, "두번째": 2, "둘째": 2,
    "세 번째": 3, "세번째": 3, "셋째": 3,
    "네 번째": 4, "네번째": 4, "넷째": 4,
    "다섯 번째": 5, "다섯번째": 5, "다섯째": 5,
}


def detect_edit_target(message: str, num_paragraphs: int) -> int | None:
    """대화 메시지가 '특정 문단 수정' 요청이면 대상 seq, 아니면 None(=새 문단으로 진행).

    수정 키워드 + 문단 지시(번호/서수/'마지막'·'방금' 등)가 함께 있어야 교체로 본다.
    """
    text = message or ""
    if num_paragraphs <= 0 or not any(k in text for k in _EDIT_KEYWORDS):
        return None
    m = re.search(r"(\d+)\s*번", text)
    if m:
        seq = int(m.group(1))
        return seq if 1 <= seq <= num_paragraphs else None
    for word, seq in _ORDINAL_WORDS.items():
        if word in text:
            return seq if seq <= num_paragraphs else num_paragraphs
    if any(r in text for r in _LAST_REFS):
        return num_paragraphs
    return None


async def assess_edit(
    gemini: GeminiClient, bible: dict, prev_paragraph: str, next_paragraph: str,
    new_body: str, objective: str | None,
) -> dict:
    """학생이 직접 고친 문단이 흐름/주제에서 과도하게 어긋나는지 판정(05-기능수정 §02).

    반환 `{weird: bool, suggestion: str|None}`. 차단하지 않고 곰 작가의 대안 제안만 만든다.
    """
    if gemini.mock or not (new_body or "").strip():
        return {"weird": False, "suggestion": None}
    brief = bible_brief(bible)
    brief_block = f"{brief}\n" if brief else ""
    obj_line = f"이번 장 주제: {objective}\n" if objective else ""
    prompt = (
        "너는 어린이 글쓰기 코치다. 학생이 직접 고쳐 쓴 한 문단이 앞뒤 문단·이야기 설정과 "
        "자연스럽게 이어지는지 본다. 대체로 괜찮으면 weird=false. 흐름이 크게 끊기거나 "
        "설정과 동떨어졌을 때만 weird=true 로 하고, 학생을 먼저 칭찬한 뒤 한두 문장으로 부드럽게 "
        "다른 방향을 제안한다(강요 아님). 결말/앞 줄거리는 언급하지 않는다.\n"
        "아래 JSON 하나만 출력(설명·코드블록 금지).\n"
        '{"weird":true|false,"suggestion":"weird 면 \'멋진 생각이야! 그런데 …\' 한두 문장, 아니면 null"}\n\n'
        f"{brief_block}{obj_line}앞 문단: {prev_paragraph or '(없음)'}\n뒤 문단: {next_paragraph or '(없음)'}\n"
        f"학생이 고친 문단: {new_body}\n\nJSON:"
    )
    try:
        import json

        raw = await gemini.generate_text(gemini.settings.gemini_model_flash_lite, prompt)
        data = json.loads(_strip_json(raw))
        if isinstance(data, dict) and isinstance(data.get("weird"), bool):
            sug = data.get("suggestion")
            return {"weird": data["weird"], "suggestion": sug if data["weird"] and sug else None}
    except Exception:
        pass
    return {"weird": False, "suggestion": None}
