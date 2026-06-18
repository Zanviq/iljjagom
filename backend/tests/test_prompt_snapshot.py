"""ai_steps 프롬프트 스냅샷 적재(관리자/01 §4-B) — emit 이 직전 LLM 프롬프트를 1회 적재·소비."""
from __future__ import annotations

from app.ai.gemini import GeminiClient, last_prompt_var
from app.ai.skills.base import _PROMPT_SNAPSHOT_MAX, SkillContext
from app.config import get_settings
from app.store import get_store


def _ctx():
    store = get_store()
    settings = get_settings()
    session = store.create_ai_session(None, "writer")
    ctx = SkillContext(
        store=store, gemini=GeminiClient(settings), settings=settings, session_id=session.id
    )
    return store, ctx, session.id


def test_emit_attaches_and_consumes_prompt():
    store, ctx, sid = _ctx()
    last_prompt_var.set("설계 프롬프트 본문입니다")
    ctx.emit("생성", "generate_text", {"role": "designer"}, {"ok": True})
    # 비-LLM 스텝: 직전에 소비됐으므로 _prompt 없음
    ctx.emit("관측", "read_my_books", {}, {"books": []})

    steps = store.list_ai_steps(sid)
    assert steps[0].args["_prompt"]["user"] == "설계 프롬프트 본문입니다"
    assert steps[0].args["role"] == "designer"      # 기존 args 보존
    assert "_prompt" not in steps[1].args            # 소비 후 비움


def test_prompt_snapshot_truncated():
    store, ctx, sid = _ctx()
    big = "가" * (_PROMPT_SNAPSHOT_MAX + 500)
    last_prompt_var.set(big)
    ctx.emit("생성", "generate_text", {}, {})
    snap = store.list_ai_steps(sid)[0].args["_prompt"]
    assert snap["chars"] == len(big)                 # 원문 길이 기록
    assert len(snap["user"]) <= _PROMPT_SNAPSHOT_MAX + 10
    assert snap["user"].endswith("…(절단)")


async def test_real_flow_records_prompt_in_step(client):
    # mock 에서도 generate_text 를 부르는 스킬은 프롬프트가 스텝에 남는다.
    from tests.conftest import auth

    th = auth("teacher_ps@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})

    store, ctx, sid = _ctx()
    await ctx.gemini.generate_text("gemini-2.5-flash", "이 문장을 요약해줘: 옛날옛적에")
    ctx.emit("요약", "generate_text", {"role": "writer"}, {"ok": True})
    steps = store.list_ai_steps(sid)
    assert steps[-1].args.get("_prompt", {}).get("user", "").startswith("이 문장을 요약")
