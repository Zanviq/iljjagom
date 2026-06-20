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
