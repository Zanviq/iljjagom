"use client";

import { useRouter } from "next/navigation";
import { useActionState, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorText } from "@/components/ui/ErrorText";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { SubmitButton } from "@/components/ui/SubmitButton";
import {
  createPromptAction,
  type PromptFormState,
} from "@/lib/teacher/actions";
import type { AssessmentType } from "@/lib/types";

const initial: PromptFormState = {};

const ASSESSMENT_OPTIONS = [
  { value: "none", label: "평가 없음" },
  { value: "quiz", label: "퀴즈" },
  { value: "essay", label: "독후감" },
];

const LANGUAGE_OPTIONS = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
];

const GRADE_OPTIONS = [
  { value: "", label: "선택 안 함" },
  ...[1, 2, 3, 4, 5, 6].map((g) => ({ value: String(g), label: `${g}학년` })),
];

const CHAPTERS_OPTIONS = [
  { value: "", label: "자동" },
  ...[4, 6, 8, 10].map((n) => ({ value: String(n), label: `${n}장` })),
];

const SAFETY_OPTIONS = [
  { value: "", label: "학급 기본값" },
  { value: "relaxed", label: "느슨하게" },
  { value: "standard", label: "표준" },
  { value: "strict", label: "엄격하게" },
];

export function PromptForm({ classId }: { classId: string }) {
  const router = useRouter();
  const [state, formAction] = useActionState(createPromptAction, initial);

  // 생성 성공 시 발제 목록(서버 컴포넌트) 갱신. (setState 없음 → effect 안전)
  useEffect(() => {
    if (state.createdId) router.refresh();
  }, [state.createdId, router]);

  return (
    <Card padding="lg">
      <form action={formAction} className="flex flex-col gap-[18px]">
        <input type="hidden" name="classId" value={classId} />

        {/* 성공할 때마다 createdId 가 바뀌어 입력 필드(로컬 상태)가 새로 마운트=초기화 */}
        <PromptFields key={state.createdId ?? "init"} />

        {state.error && <ErrorText>{state.error}</ErrorText>}
        {state.ok && (
          <p
            className="text-[length:var(--text-sm)] font-bold"
            style={{ color: "var(--success-text)" }}
          >
            발제를 냈어요!
          </p>
        )}

        <SubmitButton fullWidth size="md" icon="send" pendingText="만드는 중…">
          발제 내기
        </SubmitButton>
      </form>
    </Card>
  );
}

/** 입력 필드 묶음 — 생성 성공 시 key 변경으로 통째 초기화된다. */
function PromptFields() {
  const [objectives, setObjectives] = useState<string[]>([""]);
  const [assessmentType, setAssessmentType] = useState<AssessmentType>("none");

  return (
    <>
      <Field label="주제" required>
        <Input name="topic" required icon="pencil" placeholder="예) 물의 순환" />
      </Field>

      <div>
        <p className="mb-2 text-[length:var(--text-sm)] font-bold text-ink">
          학습 목표{" "}
          <span className="font-medium text-ink-3">(1개 이상)</span>
        </p>
        <div className="flex flex-col gap-2">
          {objectives.map((val, i) => (
            <div key={i} className="flex gap-2">
              <Input
                name="learningObjectives"
                value={val}
                onChange={(e) =>
                  setObjectives((arr) =>
                    arr.map((v, j) => (j === i ? e.target.value : v)),
                  )
                }
                placeholder="예) 증발·응결·강수 이해"
              />
              {objectives.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  icon="x"
                  aria-label="목표 삭제"
                  onClick={() =>
                    setObjectives((arr) => arr.filter((_, j) => j !== i))
                  }
                />
              )}
            </div>
          ))}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          icon="plus"
          className="mt-2"
          onClick={() => setObjectives((arr) => [...arr, ""])}
        >
          목표 추가
        </Button>
      </div>

      <div className="grid gap-3.5 sm:grid-cols-2">
        <Field label="평가 방식">
          <Select
            name="assessmentType"
            value={assessmentType}
            onChange={(e) => setAssessmentType(e.target.value as AssessmentType)}
            options={ASSESSMENT_OPTIONS}
          />
        </Field>
        <Field label="언어">
          <Select name="language" defaultValue="ko" options={LANGUAGE_OPTIONS} />
        </Field>
      </div>

      {assessmentType !== "none" && (
        <Field label="평가 상세 (선택)">
          <Input name="assessmentDetail" placeholder="예) 5문항 객관식" />
        </Field>
      )}

      <details className="rounded-[var(--radius-input)] border border-line bg-surface-2 px-4 py-3">
        <summary className="cursor-pointer text-[length:var(--text-sm)] font-bold text-ink-2">
          상세 설정 (선택)
        </summary>
        <div className="mt-3.5 flex flex-col gap-[18px]">
          <div className="grid gap-3.5 sm:grid-cols-2">
            <Field label="대상 학년">
              <Select name="gradeBand" defaultValue="" options={GRADE_OPTIONS} />
            </Field>
            <Field label="이야기 길이">
              <Select name="chaptersPlanned" defaultValue="" options={CHAPTERS_OPTIONS} />
            </Field>
          </div>
          <div className="grid gap-3.5 sm:grid-cols-2">
            <Field label="마감일">
              <Input name="dueAt" type="date" />
            </Field>
            <Field label="안전 강도">
              <Select name="safetyLevel" defaultValue="" options={SAFETY_OPTIONS} />
            </Field>
          </div>
        </div>
      </details>
    </>
  );
}
