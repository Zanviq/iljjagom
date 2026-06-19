"""인메모리 저장소 — 외부 키 없이 계약을 end-to-end 로 실행/테스트하기 위한 구현.

영속성은 없다(프로세스 메모리). 접근 제어(RLS 등가)는 서비스 계층이 담당한다.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import asdict
from typing import Any

from app.store.base import Store
from app.store.records import (
    AiSessionRecord,
    AiStepRecord,
    AuditRecord,
    BibleRecord,
    BookRecord,
    ChapterRecord,
    ChunkRecord,
    ClassPostRecord,
    ClassroomRecord,
    ClassSettingsRecord,
    EventRecord,
    LearningArtifactRecord,
    LetterRecord,
    MessageRecord,
    NotificationRecord,
    ParagraphRecord,
    PlanMessageRecord,
    ProfileRecord,
    PromptRecord,
    SafetyFlagRecord,
    TokenUsageRecord,
    WritingTurnRecord,
)
from app.util import cosine_similarity, new_id, now_iso


class InMemoryStore(Store):
    def __init__(self) -> None:
        self.profiles: dict[str, ProfileRecord] = {}
        self.classrooms: dict[str, ClassroomRecord] = {}
        self.enrollments: set[tuple[str, str]] = set()
        self.prompts: dict[str, PromptRecord] = {}
        self.books: dict[str, BookRecord] = {}
        self.bibles: dict[str, BibleRecord] = {}
        self.chapters: dict[str, ChapterRecord] = {}
        self.plan_messages: list[PlanMessageRecord] = []
        self.paragraphs: list[ParagraphRecord] = []
        self.writing_turns: list[WritingTurnRecord] = []
        self.class_posts: list[ClassPostRecord] = []
        self.class_settings: dict[str, ClassSettingsRecord] = {}
        self.chunks: list[ChunkRecord] = []
        self.safety_flags: list[SafetyFlagRecord] = []
        self.letters: list[LetterRecord] = []
        self.events: list[EventRecord] = []
        self.learning_artifacts: list[LearningArtifactRecord] = []
        # 추가기능(03)
        self.ai_sessions: dict[str, AiSessionRecord] = {}
        self.ai_steps: list[AiStepRecord] = []
        self.messages: list[MessageRecord] = []
        self.token_usage: list[TokenUsageRecord] = []
        self.notifications: list[NotificationRecord] = []
        self.settings: dict[str, Any] = {}
        self.audit: list[AuditRecord] = []
        self._rate_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        # 책 최근활동 정렬용 단조 카운터 — now_iso() 동일-마이크로초 동률에도 안정 정렬(테스트 결정성).
        self._book_tick = 0
        self._book_touch: dict[str, int] = {}

    # --- profiles ---
    def get_profile(self, user_id: str) -> ProfileRecord | None:
        return self.profiles.get(user_id)

    def upsert_profile(self, profile: ProfileRecord) -> ProfileRecord:
        if not profile.created_at:
            profile.created_at = now_iso()
        # 기존 status/display_name 보존(없던 프로필이면 기본). "이미 있으면 유지".
        existing = self.profiles.get(profile.id)
        if existing and not profile.status:
            profile.status = existing.status
        if existing and not profile.display_name:
            profile.display_name = existing.display_name
        self.profiles[profile.id] = profile
        return profile

    def list_profiles(
        self, query: str | None = None, role: str | None = None, limit: int = 200
    ) -> list[ProfileRecord]:
        q = (query or "").lower()
        rows = [
            p for p in self.profiles.values()
            if (not q or q in p.email.lower())
            and (role is None or p.role == role)
        ]
        rows.sort(key=lambda p: p.created_at, reverse=True)
        return rows[:limit]

    def update_profile_fields(self, user_id: str, **fields: Any) -> ProfileRecord:
        rec = self.profiles[user_id]
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    def count_profiles_by_role(self, role: str) -> int:
        return sum(1 for p in self.profiles.values() if p.role == role)

    # --- classrooms / enrollments ---
    def create_classroom(
        self, teacher_id: str, name: str, code: str, school_id: str | None = None
    ) -> ClassroomRecord:
        rec = ClassroomRecord(
            id=new_id(),
            teacher_id=teacher_id,
            name=name,
            code=code,
            school_id=school_id,
            created_at=now_iso(),
        )
        self.classrooms[rec.id] = rec
        return rec

    def get_classroom(self, classroom_id: str) -> ClassroomRecord | None:
        return self.classrooms.get(classroom_id)

    def update_classroom(self, classroom_id: str, **fields: Any) -> ClassroomRecord:
        rec = self.classrooms[classroom_id]
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    def get_classroom_by_code(self, code: str) -> ClassroomRecord | None:
        for c in self.classrooms.values():
            if c.code.upper() == code.upper():
                return c
        return None

    def list_classrooms_for_teacher(self, teacher_id: str) -> list[ClassroomRecord]:
        return [c for c in self.classrooms.values() if c.teacher_id == teacher_id]

    def list_classrooms_for_student(self, student_id: str) -> list[ClassroomRecord]:
        ids = {cid for (cid, sid) in self.enrollments if sid == student_id}
        return [self.classrooms[cid] for cid in ids if cid in self.classrooms]

    def count_students(self, classroom_id: str) -> int:
        return sum(1 for (cid, _) in self.enrollments if cid == classroom_id)

    def list_student_ids(self, classroom_id: str) -> list[str]:
        return [sid for (cid, sid) in self.enrollments if cid == classroom_id]

    def enroll(self, classroom_id: str, student_id: str) -> None:
        self.enrollments.add((classroom_id, student_id))

    def is_enrolled(self, classroom_id: str, student_id: str) -> bool:
        return (classroom_id, student_id) in self.enrollments

    # --- prompts ---
    def create_prompt(
        self,
        classroom_id: str,
        topic: str,
        learning_objectives: list[str],
        assessment: dict[str, Any],
        language: str,
        **options: Any,
    ) -> PromptRecord:
        rec = PromptRecord(
            id=new_id(),
            classroom_id=classroom_id,
            topic=topic,
            learning_objectives=learning_objectives,
            assessment=assessment,
            language=language,
            grade_band=options.get("grade_band"),
            chapters_planned=options.get("chapters_planned"),
            due_at=options.get("due_at"),
            status=options.get("status", "open"),
            safety_level=options.get("safety_level"),
            created_at=now_iso(),
        )
        self.prompts[rec.id] = rec
        return rec

    def get_prompt(self, prompt_id: str) -> PromptRecord | None:
        return self.prompts.get(prompt_id)

    def update_prompt(self, prompt_id: str, **fields: Any) -> PromptRecord:
        rec = self.prompts[prompt_id]
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    def list_prompts_for_class(self, classroom_id: str) -> list[PromptRecord]:
        return [p for p in self.prompts.values() if p.classroom_id == classroom_id]

    def list_books_for_prompt(self, prompt_id: str) -> list[BookRecord]:
        return sorted(
            (b for b in self.books.values() if b.prompt_id == prompt_id),
            key=lambda b: b.created_at,
        )

    # --- class_settings ---
    def get_class_settings(self, classroom_id: str) -> ClassSettingsRecord | None:
        return self.class_settings.get(classroom_id)

    def upsert_class_settings(
        self, classroom_id: str, value: dict[str, Any], updated_by: str | None
    ) -> ClassSettingsRecord:
        existing = self.class_settings.get(classroom_id)
        merged = {**(existing.value if existing else {}), **value}
        rec = ClassSettingsRecord(
            classroom_id=classroom_id, value=merged, updated_by=updated_by, updated_at=now_iso()
        )
        self.class_settings[classroom_id] = rec
        return rec

    # --- books ---
    def create_book(
        self, student_id: str, classroom_id: str | None, prompt_id: str | None
    ) -> BookRecord:
        ts = now_iso()
        rec = BookRecord(
            id=new_id(),
            student_id=student_id,
            classroom_id=classroom_id,
            prompt_id=prompt_id,
            status="planning",
            created_at=ts,
            updated_at=ts,
        )
        self.books[rec.id] = rec
        self._touch_book(rec.id)
        return rec

    def get_book(self, book_id: str) -> BookRecord | None:
        return self.books.get(book_id)

    def _touch_book(self, book_id: str) -> None:
        self._book_tick += 1
        self._book_touch[book_id] = self._book_tick

    def update_book(self, book_id: str, **fields: Any) -> BookRecord:
        rec = self.books[book_id]
        for k, v in fields.items():
            setattr(rec, k, v)
        rec.updated_at = now_iso()  # 모든 변경은 마지막 활동 시각을 갱신한다.
        self._touch_book(book_id)
        return rec

    def list_books_for_student(self, student_id: str) -> list[BookRecord]:
        return sorted(
            (b for b in self.books.values() if b.student_id == student_id),
            key=lambda b: (b.updated_at or b.created_at, self._book_touch.get(b.id, 0)),
            reverse=True,
        )

    def list_books_for_class(self, classroom_id: str) -> list[BookRecord]:
        return sorted(
            (b for b in self.books.values() if b.classroom_id == classroom_id),
            key=lambda b: (b.updated_at or b.created_at, self._book_touch.get(b.id, 0)),
            reverse=True,
        )

    # --- bibles ---
    def upsert_bible(self, book_id: str, data: dict[str, Any]) -> BibleRecord:
        rec = BibleRecord(book_id=book_id, data=data, created_at=now_iso())
        self.bibles[book_id] = rec
        return rec

    def get_bible(self, book_id: str) -> BibleRecord | None:
        return self.bibles.get(book_id)

    # --- chapters ---
    def create_chapter(self, book_id: str, idx: int, mode: str) -> ChapterRecord:
        rec = ChapterRecord(
            id=new_id(), book_id=book_id, idx=idx, mode=mode, created_at=now_iso()
        )
        self.chapters[rec.id] = rec
        return rec

    def get_chapter(self, book_id: str, idx: int) -> ChapterRecord | None:
        for c in self.chapters.values():
            if c.book_id == book_id and c.idx == idx:
                return c
        return None

    def list_chapters(self, book_id: str) -> list[ChapterRecord]:
        return sorted(
            (c for c in self.chapters.values() if c.book_id == book_id),
            key=lambda c: c.idx,
        )

    def update_chapter(self, chapter_id: str, **fields: Any) -> ChapterRecord:
        rec = self.chapters[chapter_id]
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    # --- plan messages ---
    def add_plan_message(self, book_id: str, role: str, content: str) -> PlanMessageRecord:
        rec = PlanMessageRecord(
            id=new_id(), book_id=book_id, role=role, content=content, created_at=now_iso()
        )
        self.plan_messages.append(rec)
        return rec

    def list_plan_messages(self, book_id: str) -> list[PlanMessageRecord]:
        return [m for m in self.plan_messages if m.book_id == book_id]

    # --- 자유집필 협업 (문단·턴) ---
    def add_paragraph(
        self, chapter_id: str, book_id: str, seq: int, body: str, source: str = "collab"
    ) -> ParagraphRecord:
        rec = ParagraphRecord(
            id=new_id(), chapter_id=chapter_id, book_id=book_id, seq=seq, body=body,
            source=source, created_at=now_iso(),
        )
        self.paragraphs.append(rec)
        return rec

    def list_paragraphs(self, chapter_id: str) -> list[ParagraphRecord]:
        return sorted(
            (p for p in self.paragraphs if p.chapter_id == chapter_id), key=lambda p: p.seq
        )

    def add_writing_turn(
        self, chapter_id: str, book_id: str, role: str, kind: str, content: str,
        paragraph_id: str | None = None,
    ) -> WritingTurnRecord:
        rec = WritingTurnRecord(
            id=new_id(), chapter_id=chapter_id, book_id=book_id, role=role, kind=kind,
            content=content, paragraph_id=paragraph_id, created_at=now_iso(),
        )
        self.writing_turns.append(rec)
        return rec

    def list_writing_turns(self, chapter_id: str) -> list[WritingTurnRecord]:
        return sorted(
            (t for t in self.writing_turns if t.chapter_id == chapter_id),
            key=lambda t: t.created_at,
        )

    # --- 학급 게시판 ---
    def add_class_post(
        self, classroom_id: str, book_id: str, student_id: str, title: str,
        intro: str | None, snapshot: dict[str, Any], status: str,
    ) -> ClassPostRecord:
        rec = ClassPostRecord(
            id=new_id(), classroom_id=classroom_id, book_id=book_id, student_id=student_id,
            title=title, intro=intro, snapshot=snapshot, status=status, created_at=now_iso(),
        )
        self.class_posts.append(rec)
        return rec

    def get_class_post(self, post_id: str) -> ClassPostRecord | None:
        return next((p for p in self.class_posts if p.id == post_id), None)

    def get_class_post_by_book(self, book_id: str) -> ClassPostRecord | None:
        return next((p for p in self.class_posts if p.book_id == book_id), None)

    def list_class_posts(self, classroom_id: str) -> list[ClassPostRecord]:
        return sorted(
            (p for p in self.class_posts if p.classroom_id == classroom_id),
            key=lambda p: p.created_at, reverse=True,
        )

    def update_class_post(self, post_id: str, **fields: Any) -> ClassPostRecord:
        rec = self.get_class_post(post_id)
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    # --- RAG chunks ---
    def add_chunk(
        self, book_id: str, chapter_id: str | None, content: str, embedding: list[float]
    ) -> ChunkRecord:
        rec = ChunkRecord(
            id=new_id(),
            book_id=book_id,
            chapter_id=chapter_id,
            content=content,
            embedding=embedding,
            created_at=now_iso(),
        )
        self.chunks.append(rec)
        return rec

    def search_chunks(
        self, book_id: str, query_embedding: list[float], k: int = 5
    ) -> list[ChunkRecord]:
        scored = [
            (cosine_similarity(query_embedding, c.embedding), c)
            for c in self.chunks
            if c.book_id == book_id
        ]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [c for _, c in scored[:k]]

    # --- safety ---
    def add_safety_flag(
        self,
        book_id: str | None,
        student_id: str | None,
        source: str,
        reason: str,
        category: str | None = None,
        severity: str = "normal",
        letter_id: str | None = None,
    ) -> SafetyFlagRecord:
        rec = SafetyFlagRecord(
            id=new_id(),
            book_id=book_id,
            student_id=student_id,
            source=source,
            reason=reason,
            status="open",
            category=category,
            severity=severity,
            letter_id=letter_id,
            created_at=now_iso(),
        )
        self.safety_flags.append(rec)
        return rec

    def _book_ids_for_class(self, class_id: str) -> set[str]:
        return {b.id for b in self.books.values() if b.classroom_id == class_id}

    def get_safety_flag(self, flag_id: str) -> SafetyFlagRecord | None:
        return next((f for f in self.safety_flags if f.id == flag_id), None)

    def list_safety_flags(
        self,
        class_id: str | None = None,
        book_id: str | None = None,
        status: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[SafetyFlagRecord]:
        class_books = self._book_ids_for_class(class_id) if class_id else None
        rows = [
            f for f in self.safety_flags
            if (book_id is None or f.book_id == book_id)
            and (class_books is None or f.book_id in class_books)
            and (status is None or f.status == status)
            and (source is None or f.source == source)
        ]
        rows.sort(key=lambda f: f.created_at, reverse=True)
        return rows[:limit]

    def update_safety_flag(self, flag_id: str, **fields: Any) -> SafetyFlagRecord:
        rec = self.get_safety_flag(flag_id)
        if rec is None:
            raise KeyError(flag_id)
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    # --- letters ---
    def add_letter(
        self,
        book_id: str,
        student_id: str | None,
        recipient: str,
        body: str,
        status: str = "pending",
        reply: str | None = None,
        reply_source: str | None = None,
    ) -> LetterRecord:
        rec = LetterRecord(
            id=new_id(), book_id=book_id, student_id=student_id, recipient=recipient,
            body=body, status=status, reply=reply, reply_source=reply_source,
            created_at=now_iso(),
        )
        self.letters.append(rec)
        return rec

    def get_letter(self, letter_id: str) -> LetterRecord | None:
        return next((m for m in self.letters if m.id == letter_id), None)

    def list_letters(
        self,
        class_id: str | None = None,
        book_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[LetterRecord]:
        class_books = self._book_ids_for_class(class_id) if class_id else None
        rows = [
            m for m in self.letters
            if (book_id is None or m.book_id == book_id)
            and (class_books is None or m.book_id in class_books)
            and (status is None or m.status == status)
        ]
        rows.sort(key=lambda m: m.created_at, reverse=True)
        return rows[:limit]

    def update_letter(self, letter_id: str, **fields: Any) -> LetterRecord:
        rec = self.get_letter(letter_id)
        if rec is None:
            raise KeyError(letter_id)
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    # --- events ---
    def add_events(self, student_id: str, items: list[dict[str, Any]]) -> int:
        n = 0
        for it in items:
            self.events.append(
                EventRecord(
                    id=new_id(), book_id=it.get("book_id"), student_id=student_id,
                    type=it["type"], payload=it.get("payload") or {}, created_at=now_iso(),
                )
            )
            n += 1
        return n

    def list_events(
        self,
        class_id: str | None = None,
        book_id: str | None = None,
        student_id: str | None = None,
        type: str | None = None,
        since: str | None = None,
        limit: int = 1000,
    ) -> list[EventRecord]:
        class_books = self._book_ids_for_class(class_id) if class_id else None
        rows = [
            e for e in self.events
            if (book_id is None or e.book_id == book_id)
            and (class_books is None or e.book_id in class_books)
            and (student_id is None or e.student_id == student_id)
            and (type is None or e.type == type)
            and (since is None or e.created_at >= since)
        ]
        rows.sort(key=lambda e: e.created_at, reverse=True)
        return rows[:limit]

    # --- learning_artifacts ---
    def add_learning_artifact(
        self, book_id: str, type: str, data: dict[str, Any], chapter_id: str | None = None
    ) -> LearningArtifactRecord:
        rec = LearningArtifactRecord(
            id=new_id(), book_id=book_id, type=type, data=data,
            chapter_id=chapter_id, created_at=now_iso(),
        )
        self.learning_artifacts.append(rec)
        return rec

    def list_learning_artifacts(
        self,
        book_id: str | None = None,
        class_id: str | None = None,
        type: str | None = None,
    ) -> list[LearningArtifactRecord]:
        class_books = self._book_ids_for_class(class_id) if class_id else None
        rows = [
            a for a in self.learning_artifacts
            if (book_id is None or a.book_id == book_id)
            and (class_books is None or a.book_id in class_books)
            and (type is None or a.type == type)
        ]
        rows.sort(key=lambda a: a.created_at, reverse=True)
        return rows

    # --- 관리자 집계 ---
    def usage_counts(self) -> dict[str, Any]:
        profiles = list(self.profiles.values())
        books = list(self.books.values())

        def role_n(r: str) -> int:
            return sum(1 for p in profiles if p.role == r)

        def status_n(s: str) -> int:
            return sum(1 for b in books if b.status == s)

        return {
            "users": {
                "total": len(profiles),
                "students": role_n("student"),
                "teachers": role_n("teacher"),
                "admins": role_n("admin"),
            },
            "classrooms": len(self.classrooms),
            "prompts": len(self.prompts),
            "books": {
                "total": len(books),
                "planning": status_n("planning"),
                "writing": status_n("writing"),
                "done": status_n("done"),
            },
            "chapters_written": sum(1 for c in self.chapters.values() if c.char_count > 0),
            "safety_flags": {
                "open": sum(1 for f in self.safety_flags if f.status == "open"),
                "total": len(self.safety_flags),
            },
            **self._measurement_counts(),
        }

    def _measurement_counts(self) -> dict[str, Any]:
        opened = {e.student_id for e in self.events if e.type == "chapter_open"}
        finished = {e.student_id for e in self.events if e.type == "book_finished"}
        completion = round(len(finished & opened) / len(opened), 2) if opened else 0.0
        days: dict[str, set[str]] = {}
        for e in self.events:
            if e.type in ("chapter_open", "learning_open") and e.student_id:
                days.setdefault(e.student_id, set()).add((e.created_at or "")[:10])
        active = len(days)
        revisitors = sum(1 for d in days.values() if len(d) >= 2)
        revisit = round(revisitors / active, 2) if active else 0.0

        def la_n(t: str) -> int:
            return sum(1 for a in self.learning_artifacts if a.type == t)

        return {
            "completion_rate": completion,
            "revisit_rate": revisit,
            "events_total": len(self.events),
            "learning_results": {
                "quiz": la_n("quiz"), "essay": la_n("essay"),
                "emotion": la_n("emotion"), "letter": la_n("letter"),
            },
        }

    # --- AI 세션 / ReAct 트레이스 ---
    def create_ai_session(
        self, book_id: str | None, role: str, model: str | None = None,
        user_id: str | None = None,
    ) -> AiSessionRecord:
        rec = AiSessionRecord(
            id=new_id(), book_id=book_id, role=role, model=model,
            status="running", started_at=now_iso(), user_id=user_id,
        )
        self.ai_sessions[rec.id] = rec
        return rec

    def update_ai_session(self, session_id: str, **fields: Any) -> AiSessionRecord:
        rec = self.ai_sessions[session_id]
        for k, v in fields.items():
            setattr(rec, k, v)
        return rec

    def get_ai_session(self, session_id: str) -> AiSessionRecord | None:
        return self.ai_sessions.get(session_id)

    def list_ai_sessions(
        self,
        book_id: str | None = None,
        status: str | None = None,
        role: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
    ) -> list[AiSessionRecord]:
        rows = [
            s for s in self.ai_sessions.values()
            if (book_id is None or s.book_id == book_id)
            and (status is None or s.status == status)
            and (role is None or s.role == role)
            and (since is None or s.started_at >= since)
            and (until is None or s.started_at <= until)
        ]
        rows.sort(key=lambda s: s.started_at, reverse=True)
        return rows[:limit]

    def add_ai_step(
        self, session_id: str, idx: int, thought: str | None, skill: str | None,
        args: dict[str, Any], observation: dict[str, Any],
        tokens_in: int = 0, tokens_out: int = 0, ms: int | None = None,
    ) -> AiStepRecord:
        rec = AiStepRecord(
            id=new_id(), session_id=session_id, idx=idx, thought=thought, skill=skill,
            args=args or {}, observation=observation or {},
            tokens_in=tokens_in, tokens_out=tokens_out, ms=ms, created_at=now_iso(),
        )
        self.ai_steps.append(rec)
        return rec

    def list_ai_steps(self, session_id: str) -> list[AiStepRecord]:
        return sorted(
            (s for s in self.ai_steps if s.session_id == session_id),
            key=lambda s: s.idx,
        )

    # --- messages ---
    def add_message(
        self, book_id: str | None, user_id: str | None, role: str, kind: str,
        content: str, session_id: str | None = None,
    ) -> MessageRecord:
        rec = MessageRecord(
            id=new_id(), book_id=book_id, user_id=user_id, role=role, kind=kind,
            content=content, session_id=session_id, created_at=now_iso(),
        )
        self.messages.append(rec)
        return rec

    def list_messages(self, book_id: str, kind: str | None = None) -> list[MessageRecord]:
        return sorted(
            (m for m in self.messages
             if m.book_id == book_id and (kind is None or m.kind == kind)),
            key=lambda m: m.created_at,
        )

    def list_messages_for_session(self, session_id: str) -> list[MessageRecord]:
        return sorted(
            (m for m in self.messages if m.session_id == session_id),
            key=lambda m: m.created_at,
        )

    def list_messages_admin(
        self,
        user_id: str | None = None,
        book_id: str | None = None,
        kind: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 100,
    ) -> list[MessageRecord]:
        rows = [
            m for m in self.messages
            if (user_id is None or m.user_id == user_id)
            and (book_id is None or m.book_id == book_id)
            and (kind is None or m.kind == kind)
            and (since is None or m.created_at >= since)
            and (until is None or m.created_at <= until)
        ]
        rows.sort(key=lambda m: m.created_at, reverse=True)
        return rows[:limit]

    # --- token_usage ---
    def add_token_usage(
        self, session_id: str | None, model: str,
        tokens_in: int = 0, tokens_out: int = 0, est_cost: float = 0.0,
    ) -> TokenUsageRecord:
        rec = TokenUsageRecord(
            id=new_id(), session_id=session_id, model=model,
            tokens_in=tokens_in, tokens_out=tokens_out, est_cost=est_cost,
            created_at=now_iso(),
        )
        self.token_usage.append(rec)
        return rec

    def token_usage_summary(self, since: str | None = None) -> dict[str, Any]:
        rows = [u for u in self.token_usage if since is None or u.created_at >= since]
        by_model: dict[str, dict[str, Any]] = {}
        for u in rows:
            m = by_model.setdefault(
                u.model, {"calls": 0, "tokens_in": 0, "tokens_out": 0, "est_cost": 0.0}
            )
            m["calls"] += 1
            m["tokens_in"] += u.tokens_in
            m["tokens_out"] += u.tokens_out
            m["est_cost"] += u.est_cost
        return {
            "calls": len(rows),
            "tokens_in": sum(u.tokens_in for u in rows),
            "tokens_out": sum(u.tokens_out for u in rows),
            "est_cost": sum(u.est_cost for u in rows),
            "by_model": by_model,
        }

    def token_usage_buckets(
        self, group_by: str = "model", since: str | None = None, until: str | None = None
    ) -> dict[str, Any]:
        rows = [
            u for u in self.token_usage
            if (since is None or u.created_at >= since)
            and (until is None or u.created_at <= until)
        ]

        def key_of(u) -> str:
            if group_by == "day":
                return (u.created_at or "")[:10]
            if group_by == "role":
                sess = self.ai_sessions.get(u.session_id) if u.session_id else None
                return sess.role if sess else "unknown"
            return u.model

        buckets: dict[str, dict[str, Any]] = {}
        total = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "est_cost": 0.0}
        for u in rows:
            b = buckets.setdefault(
                key_of(u), {"calls": 0, "tokens_in": 0, "tokens_out": 0, "est_cost": 0.0}
            )
            for agg, val in (("calls", 1), ("tokens_in", u.tokens_in),
                             ("tokens_out", u.tokens_out), ("est_cost", u.est_cost)):
                b[agg] += val
                total[agg] += val
        return {
            "buckets": [{"key": k, **v} for k, v in sorted(buckets.items())],
            "total": {"key": "total", **total},
        }

    # --- notifications ---
    def create_notification(
        self, title: str, body: str | None = None, level: str = "info",
        target_user_id: str | None = None, target_role: str | None = None,
        is_broadcast: bool = False,
    ) -> NotificationRecord:
        rec = NotificationRecord(
            id=new_id(), target_user_id=target_user_id, target_role=target_role,
            is_broadcast=is_broadcast, title=title, body=body, level=level,
            created_at=now_iso(),
        )
        self.notifications.append(rec)
        return rec

    def list_notifications(
        self, user_id: str, role: str, unread_only: bool = False, limit: int = 50
    ) -> list[NotificationRecord]:
        def visible(n: NotificationRecord) -> bool:
            if n.target_user_id == user_id or n.is_broadcast:
                return True
            return n.target_role is not None and n.target_role == role

        rows = [
            n for n in self.notifications
            if visible(n) and (not unread_only or n.read_at is None)
        ]
        rows.sort(key=lambda n: n.created_at, reverse=True)
        return rows[:limit]

    def mark_notification_read(self, notification_id: str, user_id: str) -> None:
        for n in self.notifications:
            if n.id == notification_id and (
                n.target_user_id == user_id or n.is_broadcast or n.target_role
            ):
                if n.read_at is None:
                    n.read_at = now_iso()
                return

    # --- app_settings ---
    def get_setting(self, key: str) -> Any | None:
        return self.settings.get(key)

    def set_setting(self, key: str, value: Any, updated_by: str | None = None) -> None:
        self.settings[key] = value

    def all_settings(self) -> dict[str, Any]:
        return dict(self.settings)

    # --- audit_log ---
    def add_audit(
        self, admin_id: str | None, action: str, target: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> AuditRecord:
        rec = AuditRecord(
            id=new_id(), admin_id=admin_id, action=action, target=target,
            detail=detail or {}, created_at=now_iso(),
        )
        self.audit.append(rec)
        return rec

    def list_audit(self, limit: int = 100) -> list[AuditRecord]:
        return sorted(self.audit, key=lambda a: a.created_at, reverse=True)[:limit]

    # --- backup ---
    def _dict_tables(self) -> dict[str, tuple[dict, Any, str]]:
        return {
            "profiles": (self.profiles, ProfileRecord, "id"),
            "classrooms": (self.classrooms, ClassroomRecord, "id"),
            "prompts": (self.prompts, PromptRecord, "id"),
            "books": (self.books, BookRecord, "id"),
            "bibles": (self.bibles, BibleRecord, "book_id"),
            "chapters": (self.chapters, ChapterRecord, "id"),
            "ai_sessions": (self.ai_sessions, AiSessionRecord, "id"),
        }

    def _list_tables(self) -> dict[str, tuple[list, Any]]:
        return {
            "plan_messages": (self.plan_messages, PlanMessageRecord),
            "learning_artifacts": (self.learning_artifacts, LearningArtifactRecord),
            "events": (self.events, EventRecord),
            "safety_flags": (self.safety_flags, SafetyFlagRecord),
            "letters": (self.letters, LetterRecord),
            "ai_steps": (self.ai_steps, AiStepRecord),
            "messages": (self.messages, MessageRecord),
            "token_usage": (self.token_usage, TokenUsageRecord),
            "notifications": (self.notifications, NotificationRecord),
            "audit_log": (self.audit, AuditRecord),
        }

    def export_tables(self, tables: list[str]) -> dict[str, list[dict[str, Any]]]:
        dt, lt = self._dict_tables(), self._list_tables()
        out: dict[str, list[dict[str, Any]]] = {}
        for t in tables:
            if t in dt:
                out[t] = [asdict(v) for v in dt[t][0].values()]
            elif t in lt:
                out[t] = [asdict(v) for v in lt[t][0]]
            elif t == "enrollments":
                out[t] = [{"classroom_id": c, "student_id": s} for (c, s) in self.enrollments]
            elif t == "app_settings":
                out[t] = [{"key": k, "value": v} for k, v in self.settings.items()]
            else:
                out[t] = []
        return out

    def import_tables(
        self, mode: str, tables: dict[str, list[dict[str, Any]]]
    ) -> dict[str, int]:
        dt, lt = self._dict_tables(), self._list_tables()
        counts: dict[str, int] = {}
        for t, rows in tables.items():
            n = 0
            if t in dt:
                coll, cls, key = dt[t]
                if mode == "overwrite":
                    coll.clear()
                for r in rows:
                    rec = cls(**r)
                    coll[getattr(rec, key)] = rec
                    n += 1
            elif t in lt:
                coll, cls = lt[t]
                if mode == "overwrite":
                    coll.clear()
                for r in rows:
                    coll.append(cls(**r))
                    n += 1
            elif t == "enrollments":
                if mode == "overwrite":
                    self.enrollments.clear()
                for r in rows:
                    self.enrollments.add((r["classroom_id"], r["student_id"]))
                    n += 1
            elif t == "app_settings":
                if mode == "overwrite":
                    self.settings.clear()
                for r in rows:
                    self.settings[r["key"]] = r["value"]
                    n += 1
            counts[t] = n
        return counts

    # --- rate limit ---
    def rate_hit(self, bucket: str, user_id: str, window: float) -> int:
        now = time.monotonic()
        dq = self._rate_hits[(bucket, user_id)]
        while dq and now - dq[0] > window:
            dq.popleft()
        dq.append(now)
        return len(dq)
