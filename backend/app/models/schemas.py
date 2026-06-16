"""API 요청/응답 스키마 — 03-기능명세서 §4/§7 의 계약을 그대로 따른다(camelCase)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.models.base import CamelModel

Role = Literal["student", "teacher", "admin"]
BookStatus = Literal["planning", "writing", "done"]
ChapterMode = Literal["free", "guided"]
ReviewStatus = Literal["pending", "ok", "revising"]


# --- 인증 / 계정 ---
class Me(CamelModel):
    id: str
    email: str
    role: Role
    grade: int | None = None
    guardian_consent: bool = False
    needs_onboarding: bool = False


class OnboardingRequest(CamelModel):
    role: Literal["student", "teacher"]
    # 학급 코드: 영숫자 4~12자만 허용(패턴 주입 방지). 대소문자 무시는 조회 시 정규화.
    class_code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]{4,12}$")
    guardian_consent: bool = False
    grade: int | None = Field(default=None, ge=1, le=12)


# --- 교사 / 발제 ---
class ClassSummary(CamelModel):
    id: str
    name: str
    school_id: str | None = None
    student_count: int = 0
    code: str | None = None


class ClassesResponse(CamelModel):
    classes: list[ClassSummary]


class Assessment(CamelModel):
    type: Literal["quiz", "essay", "none"] = "none"
    detail: str = ""


class CreatePromptRequest(CamelModel):
    topic: str = Field(min_length=1)
    learning_objectives: list[str] = Field(min_length=1)
    assessment: Assessment = Assessment()
    language: str = "ko"


class Prompt(CamelModel):
    id: str
    class_id: str
    topic: str
    learning_objectives: list[str]
    assessment: Assessment
    language: str
    created_at: str


class PromptsResponse(CamelModel):
    prompts: list[Prompt]


# --- 책 ---
class CreateBookRequest(CamelModel):
    prompt_id: str


class Book(CamelModel):
    id: str
    prompt_id: str | None = None
    class_id: str | None = None
    status: BookStatus
    title: str | None = None
    created_at: str


class ChapterMeta(CamelModel):
    idx: int
    mode: ChapterMode
    review_status: ReviewStatus
    has_illustration: bool = False


class BookDetail(CamelModel):
    id: str
    status: BookStatus
    title: str | None = None
    prompt_id: str | None = None
    class_id: str | None = None
    chapters: list[ChapterMeta] = []
    total_chapters_planned: int | None = None


# --- 기획 인터뷰 ---
class PlanMessageRequest(CamelModel):
    message: str = Field(min_length=1)


class CharacterDraft(CamelModel):
    name: str | None = None
    traits: list[str] = []


class PlanReply(CamelModel):
    reply: str
    character_draft: CharacterDraft = CharacterDraft()
    ready_to_write: bool = False


# --- 설계(Bible) ---
class DesignResponse(CamelModel):
    status: Literal["designing", "done"]
    total_chapters_planned: int | None = None


# --- 단어 도움 ---
class Word(CamelModel):
    term: str
    reading: str
    meaning: str


# --- 챕터 수정(P2) ---
class ReviseRequest(CamelModel):
    instruction: str = Field(min_length=1)


class ReviseResponse(CamelModel):
    status: Literal["revising"]


def serialize(model: CamelModel) -> dict[str, Any]:
    """응답 직렬화: camelCase alias 사용."""
    return model.model_dump(by_alias=True)
