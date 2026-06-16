"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError, createPrompt } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { AssessmentType } from "@/lib/types";

export interface PromptFormState {
  error?: string;
  ok?: boolean;
  /** 성공 시 생성된 발제 id — 폼 리셋/목록 갱신 트리거로 사용. */
  createdId?: string;
}

const ASSESSMENT_TYPES: AssessmentType[] = ["quiz", "essay", "none"];

/** 발제 생성(FR-T1). 필수값(주제, 학습목표 ≥1) 검증 후 POST /classes/{id}/prompts. */
export async function createPromptAction(
  _prev: PromptFormState,
  formData: FormData,
): Promise<PromptFormState> {
  const classId = String(formData.get("classId") ?? "");
  if (!classId) return { error: "학급 정보가 없어요." };

  const topic = String(formData.get("topic") ?? "").trim();
  const learningObjectives = formData
    .getAll("learningObjectives")
    .map((v) => String(v).trim())
    .filter(Boolean);

  const typeRaw = String(formData.get("assessmentType") ?? "none");
  const assessmentType: AssessmentType = ASSESSMENT_TYPES.includes(
    typeRaw as AssessmentType,
  )
    ? (typeRaw as AssessmentType)
    : "none";
  const assessmentDetail = String(formData.get("assessmentDetail") ?? "").trim();
  const language = String(formData.get("language") ?? "ko").trim() || "ko";

  if (!topic) return { error: "주제를 입력해 주세요." };
  if (learningObjectives.length === 0) {
    return { error: "학습 목표를 하나 이상 입력해 주세요." };
  }

  const token = await getAccessToken();
  if (!token) redirect("/login");

  let createdId: string;
  try {
    const prompt = await createPrompt(token, classId, {
      topic,
      learningObjectives,
      assessment: { type: assessmentType, detail: assessmentDetail },
      language,
    });
    createdId = prompt.id;
  } catch (e) {
    if (e instanceof ApiError) return { error: e.message };
    throw e;
  }

  revalidatePath(`/classes/${classId}/prompt`);
  return { ok: true, createdId };
}
