"use server";

import { redirect } from "next/navigation";

import { createBook } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

/** 발제를 골라 새 책 생성(FR-S1) → 기획 화면으로 이동. */
export async function startBook(formData: FormData) {
  const promptId = String(formData.get("promptId") ?? "");
  if (!promptId) return;

  const token = await getAccessToken();
  if (!token) redirect("/login");

  const book = await createBook(token, promptId);
  redirect(`/books/${book.id}/plan`);
}
