"use client";

import { useFormStatus } from "react-dom";

import { Button, type ButtonProps } from "./Button";

interface SubmitButtonProps extends Omit<ButtonProps, "type" | "loading"> {
  pendingText?: string;
}

/** form action(서버 액션)과 함께 쓰는 제출 버튼. 진행 중에는 비활성/스피너 표시. */
export function SubmitButton({
  children,
  pendingText,
  variant = "solid",
  size = "lg",
  ...props
}: SubmitButtonProps) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" loading={pending} variant={variant} size={size} {...props}>
      {pending ? (pendingText ?? "잠시만요…") : children}
    </Button>
  );
}
