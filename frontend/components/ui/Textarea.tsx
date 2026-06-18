"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/cn";

/**
 * Textarea — 여러 줄 입력(new-design_version2 forms/Textarea).
 * 기본: rows + 수동 세로 리사이즈(편지·독후감·설정 등).
 * autoGrow: 입력에 맞춰 세로로 자람(min --control-h ~ maxRows줄, 도달 시 내부 스크롤),
 *   Enter 전송/Shift+Enter 줄바꿈/IME(한글) 조합 중 오전송 방지.
 *   곰 작가 기획 대화·총괄 드로어·자유집필 우측 대화 입력에 사용.
 */
export function Textarea({
  invalid = false,
  rows = 4,
  autoGrow = false,
  maxRows = 5,
  onSubmit,
  value,
  className,
  style,
  onKeyDown,
  ...rest
}: {
  invalid?: boolean;
  autoGrow?: boolean;
  maxRows?: number;
  onSubmit?: () => void;
} & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const ref = useRef<HTMLTextAreaElement>(null);

  // value 변경(전송 후 1줄로 복귀 등)에도 높이 재계산.
  useEffect(() => {
    const el = ref.current;
    if (!autoGrow || !el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [autoGrow, value]);

  if (autoGrow) {
    return (
      <textarea
        ref={ref}
        rows={1}
        value={value}
        aria-invalid={invalid || undefined}
        className={cn("ijg-control", invalid && "is-invalid", className)}
        style={{
          minHeight: "var(--control-h)",
          maxHeight: `calc(var(--control-h) * ${maxRows})`,
          padding: "9px 14px",
          lineHeight: "var(--leading-normal)",
          resize: "none",
          overflowY: "auto",
          ...style,
        }}
        onInput={(e) => {
          const el = e.currentTarget;
          el.style.height = "auto";
          el.style.height = `${el.scrollHeight}px`;
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            onSubmit?.();
          }
          onKeyDown?.(e);
        }}
        {...rest}
      />
    );
  }

  return (
    <textarea
      rows={rows}
      value={value}
      aria-invalid={invalid || undefined}
      className={cn("ijg-control", invalid && "is-invalid", className)}
      style={{
        padding: "12px 14px",
        lineHeight: "var(--leading-normal)",
        resize: "vertical",
        ...style,
      }}
      onKeyDown={onKeyDown}
      {...rest}
    />
  );
}
