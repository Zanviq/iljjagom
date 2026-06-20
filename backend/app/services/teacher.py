"""교사 서비스 — 학급 목록, 발제 생성/조회 (FR-T1)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app.deps import CurrentUser
from app.errors import forbidden, not_found, validation_error
from app.models.schemas import (
    Assessment,
    ClassSettingsPut,
    ClassSettingsResponse,
    ClassSummary,
    CreatePromptRequest,
    DashboardHistory,
    DashboardHistoryBucket,
    DashboardResponse,
    DashboardStudent,
    DashboardSummary,
    ObjectiveAchievement,
    Prompt,
    PromptSubmission,
    PromptSubmissionCounts,
    PromptSubmissionsResponse,
    PromptSubmissionStudent,
    RotateCodeResponse,
)
from app.store.base import Store
from app.store.records import BookRecord, PromptRecord

# 학급 설정 허용 키(시크릿/모델 무단설정 차단) + 전역 기본값.
_ALLOWED_SETTING_KEYS = {"safetyLevel", "featureToggles", "boardAutoPublish"}
# featureToggles 에 제어 가능한 기능 토글을 기본값과 함께 노출(프론트가 키로 토글 렌더, 이슈3).
_SETTINGS_DEFAULTS = {
    "safetyLevel": "standard",
    "featureToggles": {"boardAutoPublish": False},
}


def compute_class_metrics(
    store: Store, class_id: str, since: str | None = None, until: str | None = None
) -> dict:
    """events·learning_artifacts 로 04 지표 산출(학급 범위). from/to(날짜) 필터 선택."""
    def _in(ts: str) -> bool:
        d = (ts or "")[:10]
        return not ((since and d < since) or (until and d > until))

    events = [e for e in store.list_events(class_id=class_id, limit=5000) if _in(e.created_at)]
    opened = {e.student_id for e in events if e.type == "chapter_open"}
    finished = {e.student_id for e in events if e.type == "book_finished"}
    completion = round(len(finished & opened) / len(opened), 2) if opened else None

    days: dict[str, set[str]] = defaultdict(set)
    for e in events:
        if e.type in ("chapter_open", "learning_open") and e.student_id:
            days[e.student_id].add((e.created_at or "")[:10])
    active = len(days)
    revisitors = sum(1 for d in days.values() if len(d) >= 2)
    revisit_rate = round(revisitors / active, 2) if active else 0.0

    arts = [a for a in store.list_learning_artifacts(class_id=class_id) if _in(a.created_at)]
    total_ans = 0
    correct = 0
    obj: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # [correct, total]
    for a in arts:
        if a.type != "quiz":
            continue
        for ans in a.data.get("answers", []):
            total_ans += 1
            is_c = bool(ans.get("correct"))
            correct += 1 if is_c else 0
            o = ans.get("objective")
            if o:
                obj[o][1] += 1
                obj[o][0] += 1 if is_c else 0
    vocab_quiz_accuracy = round(correct / total_ans, 2) if total_ans else 0.0
    objective_achievement = [
        ObjectiveAchievement(objective=o, rate=round(v[0] / v[1], 2))
        for o, v in obj.items() if v[1]
    ]
    essays_submitted = sum(1 for a in arts if a.type == "essay")

    return {
        "completion_from_events": completion,  # None 이면 호출자가 status 폴백
        "revisit_rate": revisit_rate,
        "vocab_quiz_accuracy": vocab_quiz_accuracy,
        "objective_achievement": objective_achievement,
        "essays_submitted": essays_submitted,
    }


def list_classes(store: Store, user: CurrentUser) -> list[ClassSummary]:
    classrooms = store.list_classrooms_for_teacher(user.id)
    return [
        ClassSummary(
            id=c.id,
            name=c.name,
            school_id=c.school_id,
            student_count=store.count_students(c.id),
            code=c.code,
        )
        for c in classrooms
    ]


def _summary(store: Store, c) -> ClassSummary:
    return ClassSummary(
        id=c.id, name=c.name, school_id=c.school_id,
        student_count=store.count_students(c.id), code=c.code,
    )


def create_class(store: Store, user: CurrentUser, name: str) -> ClassSummary:
    """교사 학급 생성(선생님/01). 코드는 서버 CSPRNG 생성."""
    from app.services.accounts import _generate_class_code

    code = _generate_class_code(store)
    rec = store.create_classroom(teacher_id=user.id, name=name.strip(), code=code)
    return _summary(store, rec)


def rename_class(store: Store, user: CurrentUser, class_id: str, name: str) -> ClassSummary:
    _assert_teacher_owns_class(store, user, class_id)
    rec = store.update_classroom(class_id, name=name.strip())
    return _summary(store, rec)


def rotate_class_code(store: Store, user: CurrentUser, class_id: str) -> RotateCodeResponse:
    """가입 코드 재발급(분실·유출 대응). 기존 enrollments 는 유지."""
    from app.services.accounts import _generate_class_code

    _assert_teacher_owns_class(store, user, class_id)
    code = _generate_class_code(store)
    rec = store.update_classroom(class_id, code=code)
    return RotateCodeResponse(id=rec.id, code=rec.code)


def _assert_teacher_owns_class(store: Store, user: CurrentUser, class_id: str) -> None:
    classroom = store.get_classroom(class_id)
    if not classroom:
        raise not_found("학급을 찾을 수 없습니다.")
    if user.role != "admin" and classroom.teacher_id != user.id:
        raise forbidden("자기 학급에만 발제를 만들 수 있습니다.")


def _to_prompt(rec: PromptRecord) -> Prompt:
    return Prompt(
        id=rec.id,
        class_id=rec.classroom_id,
        topic=rec.topic,
        learning_objectives=rec.learning_objectives,
        assessment=Assessment(**rec.assessment) if rec.assessment else Assessment(),
        language=rec.language,
        grade_band=getattr(rec, "grade_band", None),
        chapters_planned=getattr(rec, "chapters_planned", None),
        due_at=getattr(rec, "due_at", None),
        status=getattr(rec, "status", "open") or "open",
        safety_level=getattr(rec, "safety_level", None),
        created_at=rec.created_at,
    )


def create_prompt(
    store: Store, user: CurrentUser, class_id: str, req: CreatePromptRequest
) -> Prompt:
    _assert_teacher_owns_class(store, user, class_id)
    rec = store.create_prompt(
        classroom_id=class_id,
        topic=req.topic,
        learning_objectives=req.learning_objectives,
        assessment=req.assessment.model_dump(),
        language=req.language,
        grade_band=req.grade_band,
        chapters_planned=req.chapters_planned,
        due_at=req.due_at,
        safety_level=req.safety_level,
    )
    return _to_prompt(rec)


def update_prompt(
    store: Store, user: CurrentUser, class_id: str, prompt_id: str, req
) -> Prompt:
    _assert_teacher_owns_class(store, user, class_id)
    prompt = store.get_prompt(prompt_id)
    if not prompt or prompt.classroom_id != class_id:
        raise not_found("발제를 찾을 수 없습니다.")
    fields: dict = {}
    if req.topic is not None:
        fields["topic"] = req.topic
    if req.learning_objectives is not None:
        fields["learning_objectives"] = req.learning_objectives
    if req.assessment is not None:
        fields["assessment"] = req.assessment.model_dump()
    for k in ("grade_band", "chapters_planned", "due_at", "status", "safety_level"):
        v = getattr(req, k)
        if v is not None:
            fields[k] = v
    rec = store.update_prompt(prompt_id, **fields) if fields else prompt
    return _to_prompt(rec)


def close_prompt(store: Store, user: CurrentUser, class_id: str, prompt_id: str) -> Prompt:
    _assert_teacher_owns_class(store, user, class_id)
    prompt = store.get_prompt(prompt_id)
    if not prompt or prompt.classroom_id != class_id:
        raise not_found("발제를 찾을 수 없습니다.")
    return _to_prompt(store.update_prompt(prompt_id, status="closed"))


def class_dashboard(
    store: Store, user: CurrentUser, class_id: str,
    since: str | None = None, until: str | None = None,
) -> DashboardResponse:
    # 담당 교사(또는 admin)만. 학급 학생별 진척 + 요약 집계 (FR-T2). from/to 는 지표에 적용.
    _assert_teacher_owns_class(store, user, class_id)

    student_ids = store.list_student_ids(class_id)
    # 학생별 대표 책 = 그 학급에서 가장 최근 활동 책(목록은 updated_at desc 정렬).
    rep: dict[str, BookRecord] = {}
    for b in store.list_books_for_class(class_id):
        rep.setdefault(b.student_id, b)

    students: list[DashboardStudent] = []
    books_done = 0
    vocab_count = 0
    for sid in student_ids:
        profile = store.get_profile(sid)
        email = profile.email if profile else ""
        book = rep.get(sid)
        if not book:
            students.append(DashboardStudent(student_id=sid, student_email=email))
            continue
        chapters = store.list_chapters(book.id)
        # 선생성(prefetch)만 된 미진입 챕터는 진척에서 제외(학생/06).
        done = sum(1 for c in chapters if c.char_count > 0 and not getattr(c, "prefetched", False))
        vocab_count += sum(len(c.words) for c in chapters if not getattr(c, "prefetched", False))
        if book.status == "done":
            books_done += 1
        students.append(
            DashboardStudent(
                student_id=sid,
                student_email=email,
                book_id=book.id,
                title=book.title,
                status=book.status,
                chapters_done=done,
                total_chapters=book.total_chapters_planned,
            )
        )

    student_count = len(student_ids)
    books_started = sum(1 for sid in student_ids if sid in rep)
    status_completion = round(books_done / student_count, 2) if student_count else 0.0

    # 04 실데이터 지표(events·learning_artifacts). 완독률은 book_finished 우선, 없으면 status 폴백.
    metrics = compute_class_metrics(store, class_id, since, until)
    completion_rate = (
        metrics["completion_from_events"]
        if metrics["completion_from_events"] is not None
        else status_completion
    )
    summary = DashboardSummary(
        student_count=student_count,
        books_started=books_started,
        books_done=books_done,
        completion_rate=completion_rate,
        vocab_count=vocab_count,
        revisit_rate=metrics["revisit_rate"],
        vocab_quiz_accuracy=metrics["vocab_quiz_accuracy"],
        objective_achievement=metrics["objective_achievement"],
        essays_submitted=metrics["essays_submitted"],
    )
    return DashboardResponse(students=students, summary=summary)


def get_class_settings(store: Store, user: CurrentUser, class_id: str) -> ClassSettingsResponse:
    _assert_teacher_owns_class(store, user, class_id)
    cs = store.get_class_settings(class_id)
    return ClassSettingsResponse(value=cs.value if cs else {}, defaults=dict(_SETTINGS_DEFAULTS))


def put_class_settings(
    store: Store, user: CurrentUser, class_id: str, req: ClassSettingsPut
) -> ClassSettingsResponse:
    _assert_teacher_owns_class(store, user, class_id)
    clean: dict = {}
    for k, v in (req.value or {}).items():
        if k not in _ALLOWED_SETTING_KEYS:
            continue  # 미허용 키(시크릿/모델 등) 무시
        if k == "safetyLevel" and v not in ("relaxed", "standard", "strict"):
            raise validation_error("안전강도 값이 올바르지 않아요.", {"field": "safetyLevel"})
        clean[k] = v
    # 게시판 자동공개는 classrooms 컬럼과 동기(board.py 가 읽는 권위 소스).
    # 프론트는 featureToggles.boardAutoPublish 로 보내고, 구버전 top-level 도 허용.
    ft = clean.get("featureToggles") if isinstance(clean.get("featureToggles"), dict) else {}
    bap = ft.get("boardAutoPublish", clean.get("boardAutoPublish"))
    if bap is not None:
        store.update_classroom(class_id, board_auto_publish=bool(bap))
    cs = store.upsert_class_settings(class_id, clean, user.id)
    return ClassSettingsResponse(value=cs.value, defaults=dict(_SETTINGS_DEFAULTS))


def _period_start(ts: str, group_by: str) -> str:
    """이벤트 시각 → 버킷 시작일(day=그날, week=그 주 월요일) ISO 날짜 문자열."""
    d = (ts or "")[:10]
    if group_by != "week":
        return d
    try:
        dt = date.fromisoformat(d)
    except ValueError:
        return d
    return (dt - timedelta(days=dt.weekday())).isoformat()


def class_dashboard_history(
    store: Store, user: CurrentUser, class_id: str, group_by: str = "week",
    since: str | None = None, until: str | None = None,
) -> DashboardHistory:
    _assert_teacher_owns_class(store, user, class_id)
    group_by = "day" if group_by == "day" else "week"

    def in_range(ts: str) -> bool:
        d = (ts or "")[:10]
        if since and d < since:
            return False
        if until and d > until:
            return False
        return True

    events = [e for e in store.list_events(class_id=class_id, limit=5000) if in_range(e.created_at)]
    essays = [
        a for a in store.list_learning_artifacts(class_id=class_id)
        if a.type == "essay" and in_range(a.created_at)
    ]

    buckets: dict[str, dict] = defaultdict(
        lambda: {"active": set(), "chapters": 0, "finished": 0, "essays": 0}
    )
    for e in events:
        b = buckets[_period_start(e.created_at, group_by)]
        if e.student_id:
            b["active"].add(e.student_id)
        if e.type == "chapter_open":
            b["chapters"] += 1
        elif e.type == "book_finished":
            b["finished"] += 1
    for a in essays:
        buckets[_period_start(a.created_at, group_by)]["essays"] += 1

    out = [
        DashboardHistoryBucket(
            period_start=k, active_students=len(v["active"]), chapters_done=v["chapters"],
            books_finished=v["finished"], essays_submitted=v["essays"],
        )
        for k, v in sorted(buckets.items())
    ]
    totals = DashboardHistoryBucket(
        period_start="",
        active_students=len({e.student_id for e in events if e.student_id}),
        chapters_done=sum(b.chapters_done for b in out),
        books_finished=sum(b.books_finished for b in out),
        essays_submitted=len(essays),
    )
    return DashboardHistory(buckets=out, totals=totals)


def prompt_submissions(
    store: Store, user: CurrentUser, class_id: str, prompt_id: str
) -> PromptSubmissionsResponse:
    """발제별 참여 학생·작성 요약(선생님/05). 본문 전문은 03 열람 API로 분리."""
    _assert_teacher_owns_class(store, user, class_id)
    prompt = store.get_prompt(prompt_id)
    if not prompt or prompt.classroom_id != class_id:
        raise not_found("발제를 찾을 수 없습니다.")

    books = store.list_books_for_prompt(prompt_id)
    submissions: list[PromptSubmission] = []
    started_ids: set[str] = set()
    finished = 0
    for b in books:
        started_ids.add(b.student_id)
        if b.status == "done":
            finished += 1
        chapters = [c for c in store.list_chapters(b.id) if not getattr(c, "prefetched", False)]
        written = [c for c in chapters if c.char_count > 0]
        arts = store.list_learning_artifacts(book_id=b.id)
        prof = store.get_profile(b.student_id)
        submissions.append(PromptSubmission(
            student_id=b.student_id, student_email=prof.email if prof else "",
            book_id=b.id, title=b.title, status=b.status,
            chapters_done=len(written), total_chapters_planned=b.total_chapters_planned,
            char_total=sum(c.char_count for c in written),
            quiz_count=sum(1 for a in arts if a.type == "quiz"),
            essay_count=sum(1 for a in arts if a.type == "essay"),
            emotion_logged=any(a.type == "emotion" for a in arts),
            letter_count=sum(1 for a in arts if a.type == "letter"),
            last_activity_at=b.updated_at or b.created_at,
        ))

    enrolled_ids = store.list_student_ids(class_id)
    not_started = []
    for sid in enrolled_ids:
        if sid not in started_ids:
            prof = store.get_profile(sid)
            not_started.append(PromptSubmissionStudent(
                student_id=sid, student_email=prof.email if prof else ""
            ))
    return PromptSubmissionsResponse(
        prompt=_to_prompt(prompt),
        counts=PromptSubmissionCounts(
            enrolled=len(enrolled_ids), started=len(started_ids), finished=finished
        ),
        submissions=submissions, not_started=not_started,
    )


def list_prompts(store: Store, user: CurrentUser, class_id: str) -> list[Prompt]:
    classroom = store.get_classroom(class_id)
    if not classroom:
        raise not_found("학급을 찾을 수 없습니다.")
    # 학급 멤버(교사/학생) 또는 admin 만 열람.
    is_member = (
        user.role == "admin"
        or classroom.teacher_id == user.id
        or store.is_enrolled(class_id, user.id)
    )
    if not is_member:
        raise forbidden("이 학급의 발제를 볼 수 없습니다.")
    return [_to_prompt(p) for p in store.list_prompts_for_class(class_id)]
