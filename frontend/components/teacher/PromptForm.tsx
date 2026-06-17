"use client";

import { useRouter } from "next/navigation";
import { useActionState, useEffect, useState } from "react";

import { ErrorText } from "@/components/ui/ErrorText";
import { SubmitButton } from "@/components/ui/SubmitButton";
import {
  createPromptAction,
  type PromptFormState,
} from "@/lib/teacher/actions";
import type { AssessmentType } from "@/lib/types";

const initial: PromptFormState = {};

const ASSESSMENT_LABEL: Record<AssessmentType, string> = {
  quiz: "퀴즈",
  essay: "독후감",
  none: "평가 없음",
};

export function PromptForm({ classId }: { classId: string }) {
  const router = useRouter();
  const [state, formAction] = useActionState(createPromptAction, initial);

  // 생성 성공 시 발제 목록(서버 컴포넌트) 갱신. (setState 없음 → effect 안전)
  useEffect(() => {
    if (state.createdId) router.refresh();
  }, [state.createdId, router]);

  return (
    <form
      action={formAction}
      className="rounded-card bg-surface p-6 ring-1 ring-border"
    >
      <input type="hidden" name="classId" value={classId} />

      {/* 성공할 때마다 createdId 가 바뀌어 입력 필드(로컬 상태)가 새로 마운트=초기화 */}
      <PromptFields key={state.createdId ?? "init"} />

      {state.error && (
        <ErrorText className="mt-4">{state.error}</ErrorText>
      )}
      {state.ok && (
        <p className="mt-4 text-sm font-bold text-success-strong">발제를 냈어요! 🎉</p>
      )}

      <SubmitButton className="mt-6 w-full" pendingText="만드는 중…">
        발제 내기
      </SubmitButton>
    </form>
  );
}

/** 입력 필드 묶음 — 생성 성공 시 key 변경으로 통째 초기화된다. */
function PromptFields() {
  const [objectives, setObjectives] = useState<string[]>([""]);
  const [assessmentType, setAssessmentType] = useState<AssessmentType>("none");

  return (
    <>
      <label className="flex flex-col gap-2">
        <span className="font-bold">주제</span>
        <input
          name="topic"
          required
          placeholder="예) 물의 순환"
          className="h-12 rounded-xl border-2 border-border bg-background px-4 text-lg"
        />
      </label>

      <fieldset className="mt-5 flex flex-col gap-2">
        <legend className="font-bold">학습 목표 (1개 이상)</legend>
        {objectives.map((val, i) => (
          <div key={i} className="flex gap-2">
            <input
              name="learningObjectives"
              value={val}
              onChange={(e) =>
                setObjectives((arr) =>
                  arr.map((v, j) => (j === i ? e.target.value : v)),
                )
              }
              placeholder="예) 증발·응결·강수 이해"
              className="h-11 flex-1 rounded-xl border-2 border-border bg-background px-4"
            />
            {objectives.length > 1 && (
              <button
                type="button"
                onClick={() =>
                  setObjectives((arr) => arr.filter((_, j) => j !== i))
                }
                className="rounded-xl px-3 font-bold text-muted hover:bg-black/5"
                aria-label="목표 삭제"
              >
                ✕
              </button>
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={() => setObjectives((arr) => [...arr, ""])}
          className="self-start rounded-xl px-3 py-1 text-sm font-bold text-secondary-strong hover:bg-secondary/10"
        >
          + 목표 추가
        </button>
      </fieldset>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-2">
          <span className="font-bold">평가 방식</span>
          <select
            name="assessmentType"
            value={assessmentType}
            onChange={(e) =>
              setAssessmentType(e.target.value as AssessmentType)
            }
            className="h-12 rounded-xl border-2 border-border bg-background px-3 text-lg"
          >
            {(["none", "quiz", "essay"] as const).map((t) => (
              <option key={t} value={t}>
                {ASSESSMENT_LABEL[t]}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="font-bold">언어</span>
          <select
            name="language"
            defaultValue="ko"
            className="h-12 rounded-xl border-2 border-border bg-background px-3 text-lg"
          >
            <option value="ko">한국어</option>
            <option value="en">English</option>
          </select>
        </label>
      </div>

      {assessmentType !== "none" && (
        <label className="mt-4 flex flex-col gap-2">
          <span className="font-bold">평가 상세 (선택)</span>
          <input
            name="assessmentDetail"
            placeholder="예) 5문항 객관식"
            className="h-11 rounded-xl border-2 border-border bg-background px-4"
          />
        </label>
      )}
    </>
  );
}
