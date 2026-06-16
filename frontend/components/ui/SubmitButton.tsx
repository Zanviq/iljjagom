"use client";

import { useFormStatus } from "react-dom";

import { buttonClass, type ButtonProps } from "./Button";

interface SubmitButtonProps extends Omit<ButtonProps, "type"> {
  pendingText?: string;
}

/** form action(서버 액션)과 함께 쓰는 제출 버튼. 진행 중에는 비활성화/표시. */
export function SubmitButton({
  children,
  pendingText,
  variant = "primary",
  size = "lg",
  className,
  ...props
}: SubmitButtonProps) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className={buttonClass(variant, size, className)}
      {...props}
    >
      {pending ? (pendingText ?? "잠시만요…") : children}
    </button>
  );
}
