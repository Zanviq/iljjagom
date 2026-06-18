"""SSE 오류 견고화(학생/09) — 생성 실패 시 retryable + retryAfter 동반."""
from __future__ import annotations

import json

import app.ai.writer as writer
from tests.conftest import auth


async def _designed_book(client):
    th = auth("teacher_sse@test", "teacher")
    await client.post("/onboarding", headers=th, json={"role": "teacher", "guardianConsent": False})
    classes = (await client.get("/classes", headers=th)).json()["classes"]
    class_id, code = classes[0]["id"], classes[0]["code"]
    await client.post(f"/classes/{class_id}/prompts", headers=th,
                      json={"topic": "물", "learningObjectives": ["증발"], "assessment": {}})
    prompt_id = (await client.get(f"/classes/{class_id}/prompts", headers=th)).json()["prompts"][0]["id"]
    sh = auth("kid_sse@test", "student")
    await client.post("/onboarding", headers=sh, json={"role": "student", "classCode": code, "guardianConsent": True})
    book_id = (await client.post("/books", headers=sh, json={"promptId": prompt_id})).json()["id"]
    await client.post(f"/books/{book_id}/plan/messages", headers=sh, json={"message": "토끼"})
    await client.post(f"/books/{book_id}/design", headers=sh)
    return sh, book_id


async def test_generation_failure_emits_retryable_with_retry_after(client, monkeypatch):
    sh, book_id = await _designed_book(client)

    async def _boom(*a, **k):
        raise RuntimeError("generation down")
        yield  # async generator 형태 유지

    monkeypatch.setattr(writer, "stream_chapter", _boom)

    events = []
    async with client.stream("GET", f"/books/{book_id}/chapters/1/stream", headers=sh) as resp:
        ev = None
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                ev = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                events.append((ev, json.loads(line.split(":", 1)[1].strip())))

    err = next(d for e, d in events if e == "error")
    assert err["retryable"] is True
    assert err["retryAfter"] >= 1
