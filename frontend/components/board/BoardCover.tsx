"use client";

import { useState } from "react";

import { Icon } from "@/components/ui/Icon";

/**
 * 발표(학급 게시판) 표지 삽화. 스냅샷 coverIllustration 을 렌더하되,
 * placehold.co 자리표시자거나 로드 실패면 코드 문자열 대신 중립 표시(아이콘+제목)로 폴백(07 패턴).
 */
export function BoardCover({
  url,
  alt,
  height = 200,
}: {
  url: string;
  alt: string;
  height?: number;
}) {
  const [failed, setFailed] = useState(false);
  const isPlaceholder = /placehold\.co/i.test(url);

  if (failed || isPlaceholder) {
    return (
      <div
        role="img"
        aria-label={alt}
        className="flex w-full flex-col items-center justify-center gap-2 rounded-[var(--radius-card)]"
        style={{
          height,
          background: "var(--surface-2)",
          border: "var(--border) solid var(--line)",
        }}
      >
        <Icon name="image" size={32} strokeWidth={1.5} style={{ color: "var(--text-faint)" }} />
        <span
          className="px-4 text-center text-[length:var(--text-sm)]"
          style={{ color: "var(--text-3)" }}
        >
          {alt}
        </span>
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt={alt}
      onError={() => setFailed(true)}
      className="w-full rounded-[var(--radius-card)] object-cover shadow-[var(--elev-sm)]"
      style={{ height }}
    />
  );
}
