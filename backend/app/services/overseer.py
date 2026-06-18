"""총괄(Overseer) AI 서비스 — 학생 채팅 → 맥락 읽기 → 이동/책생성 → reply+actions.

설계: 03-디자인-개선-업그레이드/03-총괄AI-사이드바. 계약: 00 §5 / 03-기능명세서 §4.2.
- role="overseer" 의 `ai_sessions` 1개가 한 대화(sessionId). 스텝은 `ai_steps`(관리자 콘솔 노출).
- 대화는 `messages`(kind="overseer", session_id) 에 저장 → 다음 턴 맥락 유지.
- 입력은 check_safety 통과, 액션 `to` 는 화이트리스트 라우트만(app.ai.routes).
- 본인 데이터만(스킬이 user_id 스코프). mock 모드는 키워드 휴리스틱으로 결정적.
"""
from __future__ import annotations

import json
from typing import Any

from app.ai.gemini import GeminiClient
from app.ai.safety import check_input
from app.ai.sanitize import sanitize_reply
from app.ai.skills.base import Budget, SkillContext, estimate_tokens, run_skill
from app.config import Settings
from app.deps import CurrentUser
from app.models.schemas import OverseerAction, OverseerReply
from app.store.base import Store
from app.store.records import AiSessionRecord
from app.util import now_iso

_INTENTS = ("start_book", "open_book", "navigate", "info")
_HISTORY_LIMIT = 12


async def overseer_message(
    store: Store,
    gemini: GeminiClient,
    settings: Settings,
    user: CurrentUser,
    message: str,
    session_id: str | None,
    route: str | None,
) -> OverseerReply:
    session = _resolve_session(store, gemini, settings, user, session_id)
    ctx = SkillContext(
        store=store, gemini=gemini, settings=settings,
        session_id=session.id, user_id=user.id, budget=Budget(max_steps=10),
    )
    # 이어가는 세션이면 스텝 인덱스를 기존 개수부터 이어 붙인다.
    ctx._step_idx = len(store.list_ai_steps(session.id))

    # 1) 입력 안전 게이트 — 부적절(ok=False) 차단 + 정서 위험(risk) 보류. (기존 안전 루프 재사용.)
    safe = check_input(message)
    if safe.risk:
        try:
            store.add_safety_flag(
                None, user.id, "overseer", safe.reason or "정서 위험 신호 감지",
                category=safe.category, severity="high",
            )
        except Exception:
            pass
    if (not safe.ok) or safe.risk:
        ctx.emit("입력 안전 게이트(차단/보류)", "check_safety", {"kind": "input"},
                 {"ok": safe.ok, "risk": safe.risk, "reason": safe.reason})
        if safe.risk:
            reply = ("혹시 힘든 일이 있어? 그럴 땐 선생님이나 가까운 어른에게 꼭 이야기해줘. "
                     "내가 도와줄 다른 것도 있을까?")
        else:
            reply = safe.suggestion or "그건 선생님이랑 같이 이야기해보면 좋겠어. 다른 걸 도와줄까?"
        _finish(store, ctx, session, reply, [])
        return OverseerReply(session_id=session.id, reply=reply, actions=[])

    # 2) 사용자 메시지 저장(대화 연속).
    try:
        store.add_message(None, user.id, "user", "overseer", message, session_id=session.id)
    except Exception:
        pass

    # 3) 맥락 읽기(read_* 스킬 → 스텝 기록).
    books = (await run_skill(ctx, "read_my_books", {}, thought="내 책 현황 파악")).get("books", [])
    prompts = (await run_skill(ctx, "read_class_prompts", {}, thought="우리 학급 발제 파악")).get("prompts", [])
    activity = await run_skill(ctx, "read_my_activity", {}, thought="최근 활동 파악")

    # 4) 결정(reply + intent/액션 인자) — 실 LLM 또는 mock 휴리스틱.
    history = _conversation(store, session.id)
    decision = await _decide(ctx, gemini, message, history, books, prompts, activity, route)

    # 5) 액션 실행(navigate/start_new_book/open_book 스킬 → navigate 액션 수집).
    actions = await _execute(ctx, decision, books, prompts)

    # 6) reply 정제(이모지·마크다운 제거) + 예고/빈/반복 차단 → 데이터 요약 폴백.
    reply = _finalize_reply(decision, message, history, books, prompts, activity)
    _finish(store, ctx, session, reply, actions)
    return OverseerReply(
        session_id=session.id,
        reply=reply,
        actions=[OverseerAction(**a) for a in actions],
    )


# --- 세션/대화 ---


def _resolve_session(
    store: Store, gemini: GeminiClient, settings: Settings, user: CurrentUser, session_id: str | None
) -> AiSessionRecord:
    """소유한 overseer 세션이면 재개, 아니면 새 세션. (위조 sessionId 는 조용히 새로 시작.)"""
    model = settings.gemini_model_flash_lite
    if session_id:
        s = store.get_ai_session(session_id)
        if s and s.role == "overseer" and s.user_id == user.id:
            if s.status != "running":
                store.update_ai_session(s.id, status="running", ended_at=None)
            return store.get_ai_session(s.id) or s
    return store.create_ai_session(None, "overseer", model=model, user_id=user.id)


def _conversation(store: Store, session_id: str) -> list[dict[str, str]]:
    msgs = store.list_messages_for_session(session_id)
    turns = [{"role": m.role, "content": m.content} for m in msgs if m.content]
    return turns[-_HISTORY_LIMIT:]


def _finish(
    store: Store, ctx: SkillContext, session: AiSessionRecord, reply: str, actions: list[dict]
) -> None:
    ctx.emit("응답 생성", "finish", {"actionCount": len(actions)},
             {"reply": reply[:200], "actions": actions})
    try:
        store.add_message(None, ctx.user_id, "ai", "overseer", reply, session_id=session.id)
    except Exception:
        pass
    store.update_ai_session(session.id, status="done", ended_at=now_iso(), summary=reply[:120])


# --- 의사결정 ---


async def _decide(
    ctx: SkillContext,
    gemini: GeminiClient,
    message: str,
    history: list[dict],
    books: list[dict],
    prompts: list[dict],
    activity: dict,
    route: str | None,
) -> dict[str, Any]:
    if gemini.mock:
        return _decide_mock(message, books, prompts)
    model = ctx.model_for("chat")
    prompt = _decision_prompt(message, history, books, prompts, activity, route)
    try:
        raw = await gemini.generate_text(model, prompt)
        ctx.log_tokens(model, estimate_tokens(prompt), estimate_tokens(raw))
        decision = _parse_json(raw)
    except Exception:
        decision = None
    if not decision or decision.get("intent") not in _INTENTS:
        # 파싱/모델 실패 → 결정적 휴리스틱으로 폴백.
        return _decide_mock(message, books, prompts)
    return decision


def _decision_prompt(
    message: str, history: list[dict], books: list[dict], prompts: list[dict],
    activity: dict, route: str | None,
) -> str:
    ctx_books = json.dumps(books, ensure_ascii=False)[:1500]
    ctx_prompts = json.dumps(prompts, ensure_ascii=False)[:1500]
    ctx_hist = "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:]) or "(없음)"
    return (
        "너는 초등학생을 돕는 '곰 작가'라는 따뜻한 안내 AI다. 학생의 말을 읽고, 알맞은 화면으로 데려가거나 "
        "정보를 알려준다. 반드시 아래 JSON 하나만 출력한다(설명·코드블록 금지).\n"
        '{"reply": "학생에게 할 따뜻하고 쉬운 한국어 한두 문장", '
        '"intent": "start_book|open_book|navigate|info", '
        '"promptId": "start_book 일 때 고른 발제 id(없으면 생략)", '
        '"bookId": "open_book 일 때 열 책 id", '
        '"route": "navigate 일 때 이동 경로(/home·/learn 만)", "label": "버튼 글자", "auto": false}\n'
        "규칙: 새 이야기를 만들고 싶어하면 start_book(우리 반 발제 중 알맞은 promptId). "
        "기존 책을 이어보려 하면 open_book(bookId). 단순 안내/질문이면 info(액션 없음). "
        "promptId/bookId 는 아래 맥락에 있는 실제 값만 쓴다. 없으면 info.\n"
        "info 질문(진행·활동·내 책 등)이면 아래 [내 책]/[최근 활동] 데이터를 직접 요약해 답한다. "
        "'알려줄게/알려드릴게/보여줄게'처럼 예고만 하지 말고 실제 수치(책 권수·제목·진행 장수)를 바로 말한다. "
        "데이터가 비면 솔직히('아직 만든 책이 없어') 안내한다. "
        "이모지·마크다운·작업 흔적을 절대 쓰지 말고, 따뜻하고 쉬운 평문 한두 문장으로만 답한다.\n\n"
        f"[현재 화면] {route or '/home'}\n"
        f"[내 책] {ctx_books}\n"
        f"[우리 반 발제] {ctx_prompts}\n"
        f"[최근 활동] {json.dumps(activity, ensure_ascii=False)[:400]}\n"
        f"[최근 대화]\n{ctx_hist}\n\n"
        f"[학생의 말] {message}\n\nJSON:"
    )


def _parse_json(raw: str) -> dict[str, Any] | None:
    t = (raw or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.endswith("```"):
            t = t[:-3]
        if t.startswith("json"):
            t = t[4:]
    t = t.strip()
    # 본문에 섞여 있어도 첫 JSON 객체만 추출.
    if not t.startswith("{"):
        s, e = t.find("{"), t.rfind("}")
        if s == -1 or e == -1 or e <= s:
            return None
        t = t[s : e + 1]
    try:
        data = json.loads(t)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


_NEW_KW = ("만들", "새 책", "새책", "쓰고", "쓸래", "쓰기", "시작", "지어", "지을", "짓고")
_OPEN_KW = ("열어", "이어", "계속", "보던", "읽던", "마저", "이어서")
# 진행/활동/내 책 질문(학생/16: "지금까지·한 거·알려줘·보여줘" 등 누락분 보강).
_PROGRESS_KW = (
    "진행", "얼마나", "어디까지", "몇 장", "몇장", "완독", "다 썼", "진척", "현황",
    "지금까지", "한 거", "한거", "뭐 했", "뭐했", "뭐 만들", "내 책", "책 목록",
    "뭐 있", "알려줘", "알려 줘", "보여줘", "보여 줘",
)
# 예고 패턴(내용 없는 "알려줄게"류). 실제 데이터(숫자)가 없으면 폴백 대상.
_TEASER_KW = ("알려줄게", "알려 줄게", "알려드릴게", "알려 드릴게", "보여줄게", "보여 줄게",
              "알려줄께", "보여줄께")


def _is_info_query(message: str) -> bool:
    return any(k in (message or "") for k in _PROGRESS_KW)


def _looks_like_teaser(reply: str) -> bool:
    """'알려줄게'처럼 예고만 하고 실제 수치(숫자)가 없는 빈 응답인지."""
    r = reply or ""
    return any(k in r for k in _TEASER_KW) and not any(c.isdigit() for c in r)


def _data_summary(books: list[dict], prompts: list[dict]) -> str:
    """info 질문에 대한 결정적 데이터 답(실제 책 수·제목·진행 장수). reply 토대/폴백."""
    if not books:
        if prompts:
            topic = prompts[0].get("topic") or "새 주제"
            return (f"아직 만든 책이 없어. 우리 반에 '{topic}' 발제가 있으니 "
                    "'책 쓰고 싶어'라고 말하면 같이 시작할 수 있어!")
        return "아직 만든 책이 없어. 선생님이 발제를 올리면 같이 새 이야기를 시작해보자!"
    parts = ", ".join(
        f"'{b.get('title') or '제목 미정'}' {b.get('chaptersDone', 0)}/{b.get('totalChaptersPlanned') or '?'}장"
        for b in books[:3]
    )
    return f"지금까지 책 {len(books)}권을 만들었어. {parts}."


def _finalize_reply(
    decision: dict[str, Any], message: str, history: list[dict],
    books: list[dict], prompts: list[dict], activity: dict,
) -> str:
    """reply 정제 + 예고/빈/직전반복 차단 → 데이터 요약 폴백."""
    reply = sanitize_reply(decision.get("reply") or "")
    last_ai = next((h["content"] for h in reversed(history) if h.get("role") == "ai"), "")
    last_ai = sanitize_reply(last_ai)
    if decision.get("intent") == "info" and _is_info_query(message):
        if (not reply) or _looks_like_teaser(reply) or reply == last_ai:
            reply = sanitize_reply(_data_summary(books, prompts))
    if not reply:
        reply = "무엇을 도와줄까?"
    if reply == last_ai:  # 그래도 직전과 동일하면 데이터 요약으로 갈아끼움(반복 차단).
        reply = sanitize_reply(_data_summary(books, prompts)) or reply
    return reply


def _decide_mock(message: str, books: list[dict], prompts: list[dict]) -> dict[str, Any]:
    text = message or ""
    if any(k in text for k in _NEW_KW):
        if prompts:
            p = prompts[0]
            return {
                "intent": "start_book", "promptId": p["promptId"],
                "reply": f"좋아! '{p['topic']}' 이야기를 새로 시작해볼까? 아래 버튼을 누르면 바로 만들 수 있어.",
            }
        return {"intent": "info",
                "reply": "아직 우리 반에 시작할 발제가 없네. 선생님이 주제를 올리면 같이 만들어보자!"}
    if any(k in text for k in _OPEN_KW) and books:
        b = books[0]
        title = b.get("title") or "제목 없는 이야기"
        return {"intent": "open_book", "bookId": b["bookId"],
                "reply": f"'{title}'를 이어서 볼 수 있어. 아래 버튼을 눌러봐!"}
    if any(k in text for k in _PROGRESS_KW):
        return {"intent": "info", "reply": _data_summary(books, prompts)}
    if books:
        return {"intent": "info",
                "reply": f"지금 책 {len(books)}권이 있어. 새 이야기를 만들거나 이어 읽을 수 있어. 무엇을 도와줄까?"}
    return {"intent": "info",
            "reply": "안녕! 나는 곰 작가야. '책 쓰고 싶어'라고 말하면 선생님 발제로 새 이야기를 시작할 수 있어."}


# --- 액션 실행 ---


async def _execute(
    ctx: SkillContext, decision: dict[str, Any], books: list[dict], prompts: list[dict]
) -> list[dict]:
    intent = decision.get("intent")
    actions: list[dict] = []
    if intent == "start_book":
        prompt_id = decision.get("promptId")
        valid_ids = {p["promptId"] for p in prompts}
        if not prompt_id and len(prompts) == 1:
            prompt_id = prompts[0]["promptId"]
        if prompt_id and prompt_id in valid_ids:
            obs = await run_skill(
                ctx, "start_new_book", {"prompt_id": prompt_id}, thought="발제로 새 책 생성"
            )
            if obs.get("action"):
                actions.append(obs["action"])
        else:
            # 발제 미지정/모호 → 발제 선택 화면으로.
            obs = await run_skill(
                ctx, "go_to_page", {"route": "/books/new", "label": "책 만들러 가기"},
                thought="발제 선택 화면으로 이동",
            )
            if obs.get("action"):
                actions.append(obs["action"])
    elif intent == "open_book":
        book_id = decision.get("bookId")
        valid_ids = {b["bookId"] for b in books}
        if not book_id and books:
            book_id = books[0]["bookId"]
        if book_id and book_id in valid_ids:
            obs = await run_skill(ctx, "open_book", {"book_id": book_id}, thought="책 열기")
            if obs.get("action"):
                actions.append(obs["action"])
    elif intent == "navigate":
        route = decision.get("route")
        if route:
            obs = await run_skill(
                ctx, "go_to_page",
                {"route": route, "label": decision.get("label") or "이동하기",
                 "auto": bool(decision.get("auto", False))},
                thought="요청 화면으로 이동",
            )
            if obs.get("action"):
                actions.append(obs["action"])
    return actions
