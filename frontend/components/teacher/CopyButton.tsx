"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";

/** 가입 코드 복사 버튼(클립보드). 복사 후 잠시 "복사됨" 표시. */
export function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="ghost"
      size="sm"
      icon={copied ? "check" : "copy"}
      onClick={() => {
        void navigator.clipboard?.writeText(value).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
    >
      {copied ? "복사됨" : "복사"}
    </Button>
  );
}
