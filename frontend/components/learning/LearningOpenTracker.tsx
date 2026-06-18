"use client";

import { useEffect } from "react";

import { track } from "@/lib/track";

/** 학습 활동 페이지 진입 계측(추가기능 04: learning_open). 서버 컴포넌트 페이지에 삽입. */
export function LearningOpenTracker({ bookId }: { bookId: string }) {
  useEffect(() => {
    track("learning_open", { bookId });
  }, [bookId]);
  return null;
}
