"""챕터 집필 SSE 오케스트레이션 — 03-기능명세서 §5. FR-S4/S5/S7.

이벤트 순서: meta → (guided: illustration, prompt) → token* → done.
오류 시 error 이벤트. 15초마다 `: ping` 하트비트.
재연결: ?from=<charOffset> 로 이어받기.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from app.ai import chat, editor, imagen, rag, safety, writer
from app.ai.gemini import GeminiClient
from app.ai.sanitize import sanitize_body, sanitize_line
from app.ai.skills.base import estimate_tokens
from app.ai.trace import Trace
from app.deps import CurrentUser
from app.services.books import assert_can_access_book, get_book_or_404
from app.services.prefetch import acquire_prefetch, release_prefetch
from app.store.base import Store

HEARTBEAT_SECS = 15.0
# 생성 타임아웃(C2): 첫 토큰까지 / 토큰 사이 최대 간격.
FIRST_TOKEN_TIMEOUT = 25.0
TOKEN_GAP_TIMEOUT = 60.0


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _u16_len(s: str) -> int:
    """UTF-16 코드 단위 길이 — 프론트 JS `.length` 와 일치(?from= offset 정합, C7)."""
    return len(s.encode("utf-16-le")) // 2


def _u16_slice_from(s: str, start_u16: int) -> str:
    """UTF-16 단위 start 이후 부분 문자열(토큰 경계에서만 호출 → 서러게이트 분할 없음)."""
    if start_u16 <= 0:
        return s
    return s.encode("utf-16-le")[start_u16 * 2 :].decode("utf-16-le", errors="ignore")


async def _emit_token(queue: asyncio.Queue, chunk: str, running: int, from_offset: int) -> int:
    """from_offset(이미 받은 UTF-16 단위) 이후만 token 으로 보낸다. 갱신된 running(UTF-16) 반환.

    offset 단위는 프론트(JS .length=UTF-16)와 통일한다(C7).
    """
    chunk_u16 = _u16_len(chunk)
    new_running = running + chunk_u16
    if new_running <= from_offset:
        return new_running
    emit = _u16_slice_from(chunk, from_offset - running) if running < from_offset else chunk
    await queue.put(_sse("token", {"text": emit}))
    return new_running


async def _emit_text(queue: asyncio.Queue, text: str, running: int, from_offset: int) -> int:
    """문자열을 작은 조각(4자)으로 나눠 흐르듯 emit. 갱신된 running(UTF-16) 반환."""
    for i in range(0, len(text), 4):
        await asyncio.sleep(0)  # 이벤트 루프 양보(하트비트/취소 반영)
        running = await _emit_token(queue, text[i : i + 4], running, from_offset)
    return running


def _clean_segment(line: str, *, terminated: bool, has_content: bool) -> str:
    """스트리밍 한 줄을 정제해 emit·저장에 쓸 세그먼트로. 머리말 줄은 통째 생략('').

    저장본 == 스트림본 == offset 기준이 되도록, emit 한 문자열을 그대로 누적한다(08↔09 정합).
    """
    c = sanitize_line(line)
    if c is None:
        return ""                       # 머리말/헤딩 줄 → 통째 생략
    if c == "":
        return "\n" if (has_content and terminated) else ""  # 선두 빈 줄 제거, 중간은 문단 구분
    return c + ("\n" if terminated else "")


def _find_event(bible: dict, idx: int) -> dict | None:
    return next((e for e in bible.get("events", []) if e.get("chapterIdx") == idx), None)


def _student_grade(store: Store, book_id: str) -> int | None:
    """낱말 난이도 반영용 학생 학년(학생/05). 없으면 None."""
    try:
        book = store.get_book(book_id)
        prof = store.get_profile(book.student_id) if book and book.student_id else None
        return prof.grade if prof else None
    except Exception:
        return None


def _character_names(bible: dict) -> list[str]:
    """작품 고유명사(인물명) — 낱말 후보에서 제외(학생/05)."""
    return [c.get("name", "") for c in bible.get("characters", []) if c.get("name")]


def _record_complete(store: Store, book_id: str, total: int | None) -> None:
    """완독(마지막 장) 서버 파생 이벤트 — book_finished. 측정(04) 완독률 산출."""
    try:
        book = store.get_book(book_id)
        if book and book.student_id:
            store.add_events(
                book.student_id,
                [{"book_id": book_id, "type": "book_finished", "payload": {"totalChapters": total}}],
            )
    except Exception:
        pass


async def _stream_body(
    queue: asyncio.Queue,
    gemini: GeminiClient,
    bible: dict,
    event: dict,
    context: str,
    is_final: bool,
    from_offset: int,
) -> tuple[str, int]:
    """본문 토큰 스트림 — 첫 토큰 타임아웃 시 1회 재시도, 토큰 간 간격 타임아웃 감시(C2).

    (body, running[UTF-16]) 반환. 첫 토큰을 한 번도 못 받으면 재시도, 일부라도 받은 뒤
    멈추면 예외를 올려 error(retryable) 로 처리(클라이언트 ?from= 재연결).
    """
    last_exc: Exception | None = None
    for _attempt in range(2):
        body = ""        # 정제된 누적(저장·offset 기준) — 줄 단위로 정제해 emit·저장 일치(08).
        line_buf = ""    # 미완성 줄 버퍼(토큰 경계의 마크다운 분할 방지)
        running = 0
        got = False
        agen = writer.stream_chapter(gemini, bible, event, context, is_final)
        try:
            while True:
                timeout = TOKEN_GAP_TIMEOUT if got else FIRST_TOKEN_TIMEOUT
                try:
                    chunk = await asyncio.wait_for(agen.__anext__(), timeout=timeout)
                except StopAsyncIteration:
                    break
                got = True
                line_buf += chunk
                while "\n" in line_buf:
                    line, line_buf = line_buf.split("\n", 1)
                    seg = _clean_segment(line, terminated=True, has_content=bool(body))
                    if seg:
                        body += seg
                        running = await _emit_text(queue, seg, running, from_offset)
            # 마지막 미완 줄 flush(개행 없음).
            seg = _clean_segment(line_buf, terminated=False, has_content=bool(body))
            if seg:
                body += seg
                running = await _emit_text(queue, seg, running, from_offset)
            if body:
                return body, running
            # 빈 본문(토큰 0) → 재시도.
        except asyncio.TimeoutError as exc:
            last_exc = exc
            await agen.aclose()
            if got:
                raise  # 일부 전송됨 → 재시도 시 중복. error 로 넘겨 재연결에 맡김.
            continue  # 첫 토큰도 못 받음 → 재시도
        finally:
            await agen.aclose()
    if last_exc:
        raise last_exc
    raise RuntimeError("empty_generation")


async def _produce(
    queue: asyncio.Queue,
    store: Store,
    gemini: GeminiClient,
    book_id: str,
    idx: int,
    from_offset: int,
) -> None:
    """SSE 문자열을 큐에 적재. 완료/오류 시 None(sentinel) 을 넣는다."""
    try:
        book = store.get_book(book_id)
        bible_rec = store.get_bible(book_id)
        if not book or not bible_rec:
            await queue.put(
                _sse("error", {"code": "conflict", "message": "먼저 설계(design)가 필요합니다.", "retryable": False})
            )
            return

        bible = bible_rec.data
        total = bible.get("totalChaptersPlanned")
        events = bible.get("events", [])
        event = next((e for e in events if e.get("chapterIdx") == idx), None)
        if event is None:
            await queue.put(
                _sse("error", {"code": "not_found", "message": "해당 챕터가 없습니다.", "retryable": False})
            )
            return

        chapter = store.get_chapter(book_id, idx) or store.create_chapter(
            book_id, idx, event.get("mode", "free")
        )
        mode = chapter.mode
        # 전·결(guided) 진입 게이트: 기·승 완료 후 중간활동 필수(학생/15 §3).
        if mode == "guided":
            from app.services import midactivity

            if midactivity.gate_blocked(store, book_id):
                await queue.put(_sse("error", {
                    "code": "conflict",
                    "message": "중간활동을 먼저 완료해 주세요.",
                    "retryable": False,
                }))
                return
        # 이미 집필된 챕터는 저장본을 그대로 흘린다(재구독·수정/편집 반영). 첫 집필만 생성.
        served_stored = bool(chapter.body) and chapter.char_count > 0
        # 학생이 실제 진입 → 선생성(prefetch) 표식 해제(이제 chaptersDone 에 포함).
        if served_stored and chapter.prefetched:
            store.update_chapter(chapter.id, prefetched=False)
            chapter.prefetched = False

        # 1) meta (최초 1회)
        await queue.put(_sse("meta", {"chapterIdx": idx, "mode": mode, "totalChaptersPlanned": total}))

        # 2) guided 모드: 삽화 선노출 + 능동 질문 (FR-S5). 재구독 시 저장된 삽화 재사용.
        if mode == "guided":
            if chapter.illustration_path:
                url, alt = chapter.illustration_path, "이 장면의 삽화"
            else:
                url, alt = await imagen.generate_illustration(
                    gemini, book_id, idx, event.get("summary", ""), bible.get("characters", [])
                )
                # placeholder(임시)는 저장하지 않는다 — 다음 구독/선생성 때 실 삽화 재시도(박제 방지).
                if not imagen.is_placeholder_url(url):
                    store.update_chapter(chapter.id, illustration_path=url)
            await queue.put(_sse("illustration", {"url": url, "alt": alt}))
            # 능동질문 동적 생성(C6) — 본문보다 먼저. 실패해도 흐름 유지(폴백 문장).
            try:
                question = await chat.guided_prompt(gemini, bible, event)
            except Exception:
                question = "이 그림 속에서는 무슨 일이 벌어지고 있을까요?"
            await queue.put(_sse("prompt", {"text": question}))

        # 3) 본문 토큰
        running = 0
        is_final = bool(total and idx == total)
        if served_stored:
            body = chapter.body
            running = await _emit_text(queue, body, running, from_offset)
            words = chapter.words
        else:
            # 첫 집필: RAG 컨텍스트 고정 + 생성(타임아웃/재시도) + 저장 + 적재.
            context = await rag.retrieve_context(
                store, gemini, book_id, event.get("summary", ""), k=5
            )
            body, running = await _stream_body(
                queue, gemini, bible, event, context, is_final, from_offset
            )
            words = writer.select_words(
                body, _student_grade(store, book_id), _character_names(bible)
            )
            store.update_chapter(
                chapter.id, body=body, char_count=len(body), words=words, review_status="pending"
            )
            await rag.index_text(store, gemini, book_id, chapter.id, body)

        # 3b) 완료/활동 갱신 — 첫 집필·선생성 진입(served_stored) 공통(완독은 1회만).
        book_now = store.get_book(book_id)
        if is_final and body and book_now and book_now.status != "done":
            store.update_book(book_id, status="done")
            _record_complete(store, book_id, total)  # 완독 이벤트(서버 파생)
        elif not is_final and body:
            store.update_book(book_id)  # 마지막 활동 시각 갱신(이어 읽기 정렬)

        # 4) done — 다음 장 게이트: 본문이 실제로 있을 때만 다음 장 노출(생성 실패 차단, C1).
        next_available = bool(total and idx < total and body)
        await queue.put(
            _sse(
                "done",
                {
                    "chapterIdx": idx,
                    "words": words,
                    "nextChapterAvailable": next_available,
                    "charCount": _u16_len(body),
                },
            )
        )
    except Exception:
        # retryAfter: 프론트 지수 백오프 정합용 권장 재시도 간격(초). 생성 지연은 선생성(06)으로 흡수.
        await queue.put(
            _sse("error", {
                "code": "ai_unavailable",
                "message": "본문 생성 중 오류가 발생했어요.",
                "retryable": True,
                "retryAfter": 2,
            })
        )
    finally:
        await queue.put(None)


async def stream_chapter(
    store: Store,
    gemini: GeminiClient,
    user: CurrentUser,
    book_id: str,
    idx: int,
    from_offset: int = 0,
) -> AsyncIterator[str]:
    book = get_book_or_404(store, book_id)
    assert_can_access_book(store, user, book)

    queue: asyncio.Queue = asyncio.Queue()
    producer = asyncio.create_task(
        _produce(queue, store, gemini, book_id, idx, from_offset)
    )
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECS)
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # 하트비트
                continue
            if item is None:
                break
            yield item
    finally:
        producer.cancel()


# --- Tier3 편집 검수 (P2-3, 비동기) ---
async def run_first_draft_review(
    store: Store, gemini: GeminiClient, book_id: str, idx: int
) -> None:
    """챕터 초고 직후 BackgroundTask 로 호출. review_status=pending 인 챕터만 검수한다.

    학생에게 대기로 노출되지 않는다(스트림 종료 후 백그라운드). 멱등(이미 검수된 챕터는 무시).
    """
    chapter = store.get_chapter(book_id, idx)
    if not chapter or chapter.review_status != "pending" or not chapter.body:
        return
    bible_rec = store.get_bible(book_id)
    if not bible_rec:
        return
    event = _find_event(bible_rec.data, idx) or {}
    total = bible_rec.data.get("totalChaptersPlanned")
    is_final = bool(total and idx == total)
    trace = Trace(store, gemini, gemini.settings, "editor", book_id, gemini.settings.gemini_model_flash)
    objective = (event.get("objective") or "").strip()
    trace.step(
        "학습목표 도달도 점검",
        "verify_objective",
        {"objective": objective},
        {"met": bool(objective and objective in chapter.body)},
    )
    try:
        result = await editor.review_chapter(gemini, bible_rec.data, event, chapter.body, is_final)
    except Exception:
        # 편집 실패는 학생 흐름을 막지 않는다(초고 유지, 다음 기회에 재검수 가능).
        trace.end(status="error", error="editor_failed")
        store.update_chapter(chapter.id, review_status="ok")
        return
    reviewed = sanitize_body(result.body)  # 검수본도 마크다운/머리말 없는 산문으로(08)
    trace.step(
        "초고 검수·다듬기",
        "generate_text",
        {"role": "editor", "chapterIdx": idx},
        {"changed": reviewed != chapter.body, "reviewStatus": result.review_status, "notes": result.notes},
        model=gemini.settings.gemini_model_flash,
        tokens_in=estimate_tokens(chapter.body),
        tokens_out=estimate_tokens(reviewed),
    )
    # 출력 안전: 무거운 장면 신호는 교사 사후 확인용으로 기록(학생 흐름은 막지 않음).
    try:
        level = store.get_setting("safety_level") or "strict"
        out = safety.filter_output(reviewed, safety_level=str(level))
        if out.flags:
            book = store.get_book(book_id)
            store.add_safety_flag(
                book_id, book.student_id if book else None, "output",
                f"무거운 장면 신호: {', '.join(out.flags)}",
                category="heavy_scene",
            )
            trace.step("출력 안전 점검", "check_safety",
                       {"kind": "output"}, {"flags": out.flags, "softened": out.softened})
    except Exception:
        pass
    trace.end(status="done", summary=f"{idx}장 검수 완료")
    if reviewed != chapter.body:
        await rag.index_text(store, gemini, book_id, chapter.id, reviewed)
        store.update_chapter(
            chapter.id,
            body=reviewed,
            char_count=len(reviewed),
            words=writer.select_words(
                reviewed, _student_grade(store, book_id), _character_names(bible_rec.data)
            ),
            review_status=result.review_status,
        )
    else:
        store.update_chapter(chapter.id, review_status=result.review_status)


# --- 다음 장 백그라운드 선생성 (P1, 학생/06) ---
async def prefetch_chapter(
    store: Store, gemini: GeminiClient, book_id: str, idx: int
) -> None:
    """다음 장 본문(+guided 삽화)을 미리 생성·저장(스트림 없음). 멱등·단일성.

    학생이 현재 장을 읽는 동안 호출 → 진입 시 served_stored 경로로 즉시 스트리밍.
    실패해도 학생 흐름 불변(진입 시 첫 집필 경로로 폴백).
    """
    bible_rec = store.get_bible(book_id)
    if not bible_rec:
        return
    bible = bible_rec.data
    total = bible.get("totalChaptersPlanned")
    if not total or idx < 1 or idx > total:
        return
    event = _find_event(bible, idx)
    if event is None:
        return
    chapter = store.get_chapter(book_id, idx) or store.create_chapter(
        book_id, idx, event.get("mode", "free")
    )
    if chapter.body and chapter.char_count > 0:
        return  # 이미 준비됨
    if chapter.mode == "free":
        return  # free(기·승)는 협업 집필이라 선생성 안 함(학생/15)
    if not acquire_prefetch(book_id, idx):
        return  # 진행 중(중복 방지)

    trace = Trace(store, gemini, gemini.settings, "writer", book_id, gemini.settings.gemini_model_flash)
    try:
        # 삽화 먼저(가장 느린 구간) — guided + 미생성일 때만. placeholder 는 저장 안 함(학생/07).
        if not chapter.illustration_path:
            url, _alt = await imagen.generate_illustration(
                gemini, book_id, idx, event.get("summary", ""), bible.get("characters", [])
            )
            if not imagen.is_placeholder_url(url):
                store.update_chapter(chapter.id, illustration_path=url)
        is_final = bool(total and idx == total)
        context = await rag.retrieve_context(store, gemini, book_id, event.get("summary", ""), k=5)
        raw = "".join(
            [c async for c in writer.stream_chapter(gemini, bible, event, context, is_final)]
        )
        body = sanitize_body(raw)  # 스트림 경로와 동일 정제(학생/08)
        if not body:
            trace.end(status="error", error="empty_prefetch")
            return
        words = writer.select_words(body, _student_grade(store, book_id), _character_names(bible))
        store.update_chapter(
            chapter.id, body=body, char_count=len(body), words=words,
            review_status="pending", prefetched=True,  # 진입 전까지 chaptersDone 제외
        )
        await rag.index_text(store, gemini, book_id, chapter.id, body)
        # prefetch 단계에선 책 상태를 done 으로 올리지 않는다(학생 미진입). 진입 시 _produce 가 처리.
        trace.step("다음 장 선생성", "prefetch_chapter", {"chapterIdx": idx},
                   {"chars": len(body), "illustration": bool(chapter.illustration_path)})
        trace.end(status="done", summary=f"{idx}장 선생성(prefetch)")
    except Exception:
        trace.end(status="error", error="prefetch_failed")
    finally:
        release_prefetch(book_id, idx)


async def post_stream_tasks(
    store: Store, gemini: GeminiClient, book_id: str, idx: int
) -> None:
    """스트림 종료 후: 현재 장 검수 → 다음 장 선생성(순차). BackgroundTask 진입점."""
    await run_first_draft_review(store, gemini, book_id, idx)
    await prefetch_chapter(store, gemini, book_id, idx + 1)


async def prefetch_arc(store: Store, gemini: GeminiClient, book_id: str) -> None:
    """기·승 완료 후 전·결(guided) 챕터를 백그라운드 선생성(학생/15 §3).

    학생이 중간활동을 푸는 동안 가장 느린 구간(전·결 본문·삽화)을 미리 만든다. 순차·멱등.
    """
    bible_rec = store.get_bible(book_id)
    if not bible_rec:
        return
    for ev in bible_rec.data.get("events", []):
        if ev.get("mode") == "guided" and ev.get("chapterIdx"):
            await prefetch_chapter(store, gemini, book_id, ev["chapterIdx"])


# --- 자유모드 수정요청 파이프라인 (P2-2, 비동기) ---
async def run_revise(
    store: Store, gemini: GeminiClient, book_id: str, idx: int, instruction: str
) -> None:
    """대화 AI(요청 해석) → 집필 AI(재생성) → 편집 검수 → 반영. BackgroundTask 로 호출."""
    chapter = store.get_chapter(book_id, idx)
    if not chapter or not chapter.body:
        return
    bible_rec = store.get_bible(book_id)
    if not bible_rec:
        return
    bible = bible_rec.data
    event = _find_event(bible, idx) or {}
    total = bible.get("totalChaptersPlanned")
    is_final = bool(total and idx == total)

    store.update_chapter(chapter.id, review_status="revising")
    trace = Trace(store, gemini, gemini.settings, "writer", book_id, gemini.settings.gemini_model_flash)
    try:
        directive = await chat.interpret_revision(gemini, instruction)
        trace.step("수정 요청 해석", "tutor_answer", {"instruction": instruction}, {"directive": directive},
                   model=gemini.settings.gemini_model_flash_lite,
                   tokens_in=estimate_tokens(instruction), tokens_out=estimate_tokens(directive))
        context = await rag.retrieve_context(
            store, gemini, book_id, event.get("summary", ""), k=5
        )
        trace.step("관련 설정 인출", "retrieve_context", {"query": event.get("summary", ""), "k": 5},
                   {"chars": len(context)})
        revised = await writer.revise_text(
            gemini, bible, event, context, chapter.body, directive
        )
        trace.step("요청 반영해 재집필", "generate_text", {"role": "writer", "chapterIdx": idx},
                   {"chars": len(revised)}, model=gemini.settings.gemini_model_flash,
                   tokens_in=estimate_tokens(chapter.body), tokens_out=estimate_tokens(revised))
        result = await editor.review_chapter(gemini, bible, event, revised, is_final)
        trace.step("수정본 검수", "generate_text", {"role": "editor"},
                   {"reviewStatus": result.review_status}, model=gemini.settings.gemini_model_flash,
                   tokens_in=estimate_tokens(revised), tokens_out=estimate_tokens(result.body))
    except Exception:
        # 실패 시 원본 유지 + 상태 복구.
        trace.end(status="error", error="revise_failed")
        store.update_chapter(chapter.id, review_status="ok")
        return

    trace.end(status="done", summary=f"{idx}장 수정 반영")
    revised_body = sanitize_body(result.body)  # 수정본도 산문 정제(08)
    await rag.index_text(store, gemini, book_id, chapter.id, revised_body)
    store.update_chapter(
        chapter.id,
        body=revised_body,
        char_count=len(revised_body),
        words=writer.select_words(
            revised_body, _student_grade(store, book_id), _character_names(bible)
        ),
        review_status=result.review_status,
    )
    store.update_book(book_id)  # 마지막 활동 시각 갱신(이어 읽기 정렬)
