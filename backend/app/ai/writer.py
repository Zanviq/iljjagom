"""Tier2 집필 AI (Gemini 2.5 Flash, 챕터마다, SSE) — RAG 컨텍스트 고정 본문 생성.

stream_chapter 는 본문 조각(token)을 비동기로 yield 한다.
SSE 오케스트레이션(meta/illustration/prompt/token/done)은 서비스 계층이 담당.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from app.ai.brief import bible_brief
from app.ai.gemini import GeminiClient


def fallback_chapter(
    bible: dict[str, Any], event: dict[str, Any], is_final: bool = False
) -> str:
    """생성 실패/스톨 시 쓰는 결정적 본문(이슈a). 완독이 막히지 않도록 마지막 장도 매듭짓는다."""
    return _mock_chapter_text(bible, event, is_final)


def build_prompt(
    bible: dict[str, Any], event: dict[str, Any], rag_context: str, is_final: bool = False
) -> str:
    chars = ", ".join(c.get("name", "") for c in bible.get("characters", []))
    tone = bible.get("world", {}).get("tone", "따뜻한")
    objective = event.get("objective")
    obj_line = f"이 장에서 자연스럽게 담을 학습 내용: {objective}\n" if objective else ""
    if is_final:
        # 마지막 장: 비공개 후반 큰줄기(secretArc)를 회수해 자연스럽게 매듭짓는다.
        arc = (bible.get("secretArc") or {}).get("outline", "")
        ending_line = (
            "이 장은 이야기의 마지막 장이다. 다음 큰 흐름을 자연스럽게 매듭지어 결말을 완성한다: "
            f"{arc}\n"
        )
    else:
        ending_line = "결말을 미리 드러내지 말고 이 장면만 생생히 묘사한다.\n"
    return (
        "너는 어린이 동화 작가다. 초등학생이 읽기 쉬운 한국어로 한 챕터를 쓴다. "
        f"분위기는 {tone}. 등장인물: {chars}. "
        f"{ending_line}"
        f"{obj_line}"
        f"참고(설정/이전 내용):\n{rag_context}\n\n"
        f"이번 장 개요: {event.get('summary', '')}\n\n"
        f"{_OUTPUT_RULE}\n본문:"
    )


# 출력 형식 제약(08): 마크다운·제목/장번호/머리말·메타 금지, 산문만.
_OUTPUT_RULE = (
    "규칙: 마크다운 기호(**, *, #, -, > 등)를 쓰지 마라. 장 제목·장 번호·'첫 번째 순간' 같은 "
    "소제목이나 머리말을 붙이지 마라. 설명·메모·따옴표 안내 없이 이야기 본문만 자연스러운 산문으로 출력하라."
)


def _mock_chapter_text(
    bible: dict[str, Any], event: dict[str, Any], is_final: bool = False
) -> str:
    hero = "주인공"
    chars = bible.get("characters", [])
    if chars:
        hero = chars[0].get("name", "주인공")
    objective = event.get("objective") or "새로운 것"
    if is_final:
        arc = (bible.get("secretArc") or {}).get("outline", "모두가 성장했어요")
        return (
            f"{hero}은(는) 그동안 배운 '{objective}'을(를) 모두 떠올렸어요. "
            f"마침내 모든 실마리가 하나로 모였어요.\n"
            f"{arc} 그렇게 이야기는 따뜻하게 매듭지어졌답니다. 끝."
        )
    return (
        f"{hero}은(는) 오늘도 호기심 가득한 눈으로 길을 나섰어요. "
        f"오늘은 '{objective}'에 대해 알아보기로 한 날이거든요.\n"
        f"\"이게 정말 그렇게 되는 걸까?\" {hero}은(는) 고개를 갸웃했어요. "
        f"바람이 살랑 불어오자, 작은 단서 하나가 눈앞에 나타났어요.\n"
        f"{hero}은(는) 한 걸음 더 가까이 다가가 보았어요. "
        f"두근거리는 마음으로, 이야기는 이제 막 시작되고 있었답니다."
    )


# 조사·어미 접미(긴 것 우선 절단 → 표제어 근사). 형태소 분석기 없이 휴리스틱(학생/05).
_JOSA = (
    "으로써", "으로서", "에서의", "에게서", "이라고", "에서", "에게", "께서", "라고",
    "으로", "로서", "로써", "처럼", "보다", "마저", "조차", "까지", "부터", "이나",
    "에는", "에도", "에만", "한테", "이라", "에", "의", "을", "를", "은", "는",
    "이", "가", "와", "과", "도", "만", "랑", "께", "로", "야",
)
# 흔한 기능어·빈출어(학습 가치 낮음) 제외.
_STOPWORDS = {
    "이야기", "우리", "그것", "그리고", "그래서", "하지만", "그러나", "오늘", "정말",
    "너무", "모두", "다시", "조금", "많이", "서로", "무엇", "어떻게", "그때", "이제",
    "처음", "사람", "생각", "마음", "모습", "소리", "이렇게", "저렇게", "그렇게", "자신",
}
# 용언(동사/형용사) 활용 어미 — 명사 위주 선정을 위해 제외('도착했어요'·'따스한' 등).
_PREDICATE_END = (
    "습니다", "았어요", "었어요", "였어요", "했어요", "겠어요", "드려요", "았다", "었다",
    "였다", "한다", "는다", "해요", "돼요", "아요", "어요", "여요", "았던", "었던", "한",
)


def _lemma(token: str) -> str:
    """어절에서 조사/어미를 한 번 잘라 표제 근사('계곡에'→'계곡')."""
    for j in sorted(_JOSA, key=len, reverse=True):
        if token.endswith(j) and len(token) - len(j) >= 2:
            return token[: -len(j)]
    return token


def _has_korean(s: str) -> bool:
    return any("가" <= ch <= "힣" for ch in s)


def proper_nouns(bible: dict[str, Any]) -> list[str]:
    """작품 고유명사 — 낱말 후보에서 제외(인물명 + 제목 토큰, 이슈1).

    제목의 지명/고유명("초록산" 등)이 일반어로 잘못 풀이되지 않게 후보에서 뺀다.
    """
    out: list[str] = []
    for c in bible.get("characters", []) or []:
        if isinstance(c, dict):
            n = (c.get("name") or "").strip()
            if n:
                out.append(n)
    title = bible.get("title")
    if isinstance(title, str):
        for w in title.split():
            w = w.strip()
            if len(w) >= 2:
                out.append(w)
    return out


def select_words(
    text: str, grade: int | None = None, exclude: list[str] | None = None
) -> list[str]:
    """단어 도움 후보 선정(학생/05): 표제어화·불용어/고유명사 제외·학년 난이도·전체 스캔 상위 N.

    grade 낮으면 짧은 단어도 허용, 높으면 더 긴(어려운) 단어 우선. exclude 는 작품 고유명사.
    """
    # 고학년(5+)은 짧은(쉬운) 단어를 배제해 난도를 올린다. 그 외는 2글자 명사 허용.
    min_len = 3 if (grade or 3) >= 5 else 2
    exclude_set: set[str] = set()
    for name in exclude or []:
        if name:
            exclude_set.add(name)
            exclude_set.add(_lemma(name))

    freq: dict[str, int] = {}
    order: list[str] = []
    for raw in text.replace("\n", " ").split(" "):
        tok = "".join(ch for ch in raw if ch.isalnum())
        if not tok or not _has_korean(tok) or tok.endswith(_PREDICATE_END):
            continue  # 빈 토큰·비한글·용언(활용형) 제외
        lemma = _lemma(tok)
        if (
            len(lemma) < min_len
            or lemma in _STOPWORDS
            or lemma in exclude_set
        ):
            continue
        if lemma not in freq:
            order.append(lemma)
        freq[lemma] = freq.get(lemma, 0) + 1

    # 점수: 긴 단어(어려움) 우선, 희소(빈도 낮음) 우선, 동점은 본문 등장 순.
    ranked = sorted(order, key=lambda w: (-len(w), freq[w], order.index(w)))
    return ranked[:5]


async def stream_chapter(
    gemini: GeminiClient,
    bible: dict[str, Any],
    event: dict[str, Any],
    rag_context: str,
    is_final: bool = False,
) -> AsyncIterator[str]:
    """본문 토큰 스트림. is_final 이면 마지막 장 결말(secretArc) 회수."""
    if gemini.mock:
        text = _mock_chapter_text(bible, event, is_final)
        # 글자 단위 흐름을 흉내 내어 작은 조각으로 흘린다.
        for i in range(0, len(text), 4):
            await asyncio.sleep(0)  # 이벤트 루프 양보
            yield text[i : i + 4]
        return

    prompt = build_prompt(bible, event, rag_context, is_final)
    async for chunk in gemini.stream_text(gemini.settings.gemini_model_flash, prompt):
        yield chunk


async def write_paragraph(
    gemini: GeminiClient,
    bible: dict[str, Any],
    event: dict[str, Any],
    prev_paragraphs: list[str],
    student_intent: str,
    rag_context: str,
) -> str:
    """학생 의도 + 직전 문단들 + 설정으로 '한 문단'만 생성(학생/15 협업). 통짜 챕터 금지.

    초등 2~4문장. 결말/secretArc 는 미리 드러내지 않는다(기·승 단계). 호출자가 sanitize.
    """
    chars = bible.get("characters", [])
    hero = chars[0].get("name", "주인공") if chars else "주인공"
    if gemini.mock:
        intent = " ".join((student_intent or "").split()).rstrip(".!? ")
        lead = f"{hero}은(는) {intent}." if intent else f"{hero}은(는) 한 걸음 더 나아갔어요."
        return f"{lead} 그러자 이야기에 작은 변화가 살며시 찾아왔어요."

    tone = bible.get("world", {}).get("tone", "따뜻한")
    prev = "\n".join(prev_paragraphs[-3:]) or "(이번이 첫 문단)"
    brief = bible_brief(bible, event)
    brief_block = f"{brief}\n\n" if brief else ""
    prompt = (
        "너는 어린이 동화 작가다. 학생과 한 문단씩 함께 이야기를 짓는다. "
        f"분위기는 {tone}. 아래 [이야기 설정]의 인물·세계를 반영해 학생의 의도를 살려 "
        "**딱 한 문단(2~4문장)** 만 쓴다. 통짜로 길게 쓰지 마라. "
        "결말이나 앞으로의 줄거리는 미리 드러내지 않는다.\n"
        f"{_OUTPUT_RULE}\n"
        f"{brief_block}"
        f"참고(이전 내용):\n{rag_context}\n\n"
        f"직전 문단들:\n{prev}\n\n학생의 의도: {student_intent}\n\n이어질 한 문단:"
    )
    text = await gemini.generate_text(gemini.settings.gemini_model_flash, prompt)
    return text.strip()


async def revise_text(
    gemini: GeminiClient,
    bible: dict[str, Any],
    event: dict[str, Any],
    rag_context: str,
    current_body: str,
    directive: str,
) -> str:
    """수정 요청(해석된 directive)을 반영해 챕터 전체 본문을 재생성한다(비스트림).

    자유모드 수정요청(FR-S6) 파이프라인의 집필 단계. 결말은 새로 만들지 않는다.
    """
    if gemini.mock:
        hero = "주인공"
        chars = bible.get("characters", [])
        if chars:
            hero = chars[0].get("name", "주인공")
        # 결정적 재생성: 기존 본문 + 수정 directive 를 반영한 단락을 덧붙인다.
        return (
            current_body.rstrip()
            + f"\n\n{hero}은(는) 마음을 고쳐먹었어요. ({directive}) "
            f"그러자 이야기는 한결 또렷해졌답니다."
        )

    prompt = (
        "너는 어린이 동화 작가다. 아래 본문을 독자의 요청에 맞게 자연스럽게 고쳐 쓴다. "
        "결말을 새로 만들지 말고, 이 장면의 흐름은 유지한 채 요청만 반영한다. "
        "고친 전체 본문만 출력한다.\n"
        f"{_OUTPUT_RULE}\n"
        f"분위기 참고: {bible.get('world', {}).get('tone', '따뜻한')}\n"
        f"설정 참고:\n{rag_context}\n\n"
        f"독자 요청: {directive}\n\n현재 본문:\n{current_body}\n\n고친 본문:"
    )
    return (await gemini.generate_text(gemini.settings.gemini_model_flash, prompt)).strip()


async def revise_paragraph(
    gemini: GeminiClient,
    bible: dict[str, Any],
    event: dict[str, Any],
    current_paragraph: str,
    directive: str,
    rag_context: str = "",
) -> str:
    """협업 문단 '한 개'를 지시(directive)대로 고쳐 쓴다(05-기능수정 §02). 한 문단 유지.

    챕터 전체가 아니라 대상 문단만 교체. 결말/secretArc 는 드러내지 않는다(기·승 단계).
    """
    if gemini.mock:
        base = " ".join((current_paragraph or "").split()).rstrip(".!? ")
        want = " ".join((directive or "").split()).rstrip(".!? ")
        if want:
            return f"{base}. 이번엔 {want}, 그래서 장면이 한결 또렷해졌어요."
        return f"{base}. 그러자 이야기가 조금 더 또렷해졌어요."

    brief = bible_brief(bible, event)
    brief_block = f"{brief}\n\n" if brief else ""
    prompt = (
        "너는 어린이 동화 작가다. 아래 '현재 문단'을 학생 요청에 맞게 자연스럽게 고쳐 쓴다. "
        "**딱 한 문단(2~4문장)** 으로 유지하고, 통짜로 늘리지 마라. "
        "결말이나 앞으로의 줄거리는 미리 드러내지 않는다. 고친 한 문단만 출력한다.\n"
        f"{_OUTPUT_RULE}\n"
        f"{brief_block}"
        f"참고(이전 내용):\n{rag_context or '(없음)'}\n\n"
        f"학생 요청: {directive}\n\n현재 문단:\n{current_paragraph}\n\n고친 한 문단:"
    )
    return (await gemini.generate_text(gemini.settings.gemini_model_flash, prompt)).strip()
