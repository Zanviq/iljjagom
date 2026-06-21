"""설계(Bible) 정규화 — events 완전성·free/guided 분할 강제(이슈a 재발 방지)."""
from __future__ import annotations

from app.ai.designer import _normalize_bible


def test_normalize_fills_missing_events():
    # LLM 이 1장 event 만 준 경우 → 1..6 으로 완전히 채워야 한다(6장 누락 방지).
    data = {
        "totalChaptersPlanned": 6,
        "events": [{"chapterIdx": 1, "mode": "free", "objective": "증발", "summary": "s1"}],
    }
    out = _normalize_bible(data, ["증발", "응결"], 6)
    idxs = [e["chapterIdx"] for e in out["events"]]
    assert idxs == [1, 2, 3, 4, 5, 6]
    assert out["totalChaptersPlanned"] == 6
    assert out["events"][0]["summary"] == "s1"  # 기존 값 보존


def test_normalize_enforces_free_guided_split():
    out = _normalize_bible({"totalChaptersPlanned": 6, "events": []}, ["증발"], 6)
    modes = {e["chapterIdx"]: e["mode"] for e in out["events"]}
    assert modes[1] == "free" and modes[3] == "free"      # 앞 절반 free
    assert modes[4] == "guided" and modes[6] == "guided"  # 뒤 절반 guided


def test_normalize_handles_malformed_total():
    out = _normalize_bible({"events": []}, ["증발"], 6)  # total 누락
    assert out["totalChaptersPlanned"] == 6
    assert len(out["events"]) == 6


def test_normalize_coerces_string_world_and_characters():
    # 실 Gemini 가 world 를 문자열, characters 를 문자열 리스트로 주는 경우(협업 500 원인) 정규화.
    out = _normalize_bible(
        {"world": "큰 산속 울창한 숲", "characters": ["폴짝이", {"name": "깡총이"}], "events": []},
        ["증발"], 6,
    )
    assert isinstance(out["world"], dict)
    assert out["world"]["setting"] == "큰 산속 울창한 숲"
    assert all(isinstance(c, dict) for c in out["characters"])
    assert out["characters"][0]["name"] == "폴짝이"


def test_build_prompt_survives_malformed_bible():
    # world/characters 가 문자열이어도 build_prompt 가 AttributeError 없이 동작해야 한다.
    from app.ai.writer import build_prompt

    bible = {"world": "숲", "characters": ["토끼"], "title": "t"}
    p = build_prompt(bible, {"summary": "s", "objective": "증발"}, "")
    assert "따뜻한" in p  # tone 기본값 적용(크래시 없음)


def test_normalize_coerces_string_secret_arc():
    # 실 Gemini 가 secretArc 를 문자열로 주는 경우(결말 장 폴백 500 원인) dict 로 정규화.
    out = _normalize_bible({"secretArc": "모두가 함께 성장한다", "events": []}, ["증발"], 6)
    assert isinstance(out["secretArc"], dict)
    assert out["secretArc"]["outline"] == "모두가 함께 성장한다"


def test_final_fallback_and_prompt_survive_string_secret_arc():
    # secretArc 가 문자열이어도 결말 장 폴백/집필 프롬프트가 AttributeError 없이 동작해야 한다.
    # (10차 6장 라이브 500 의 실제 원인: fallback_chapter -> _mock_chapter_text 의 secretArc.get)
    from app.ai.writer import build_prompt, fallback_chapter

    bible = {"world": "숲", "characters": ["토끼"], "title": "t", "secretArc": "비밀 결말 줄거리"}
    event = {"summary": "s", "objective": "증발"}
    body = fallback_chapter(bible, event, is_final=True)
    assert body and "끝" in body  # 결말 폴백 본문 생성(크래시 없음)
    p = build_prompt(bible, event, "", is_final=True)
    assert "비밀 결말 줄거리" in p  # secretArc 문자열이 outline 으로 회수됨
