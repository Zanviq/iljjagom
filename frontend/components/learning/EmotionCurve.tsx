import { Card } from "@/components/ui/Card";
import type { EmotionPoint } from "@/lib/types";

/** 감정 곡선: value(0~1)를 챕터 순서대로 잇는 선 그래프(accent stroke). null 값은 0으로 처리. */
export function EmotionCurve({ points }: { points: EmotionPoint[] }) {
  const W = 600;
  const H = 180;
  const padX = 40;
  const padY = 34;
  const innerW = W - padX * 2;
  const innerH = H - padY * 2;
  const n = points.length;
  const x = (i: number) => (n === 1 ? W / 2 : padX + (innerW * i) / (n - 1));
  const y = (v: number | null) =>
    padY + innerH * (1 - Math.max(0, Math.min(1, v ?? 0)));
  const line = points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ");

  return (
    <Card padding="lg" className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-[200px] w-full min-w-[480px]"
        role="img"
        aria-label="감정 곡선"
      >
        {n > 1 && (
          <polyline
            points={line}
            fill="none"
            stroke="var(--accent)"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={x(i)} cy={y(p.value)} r={6} fill="var(--accent)" />
            {p.label && (
              <text
                x={x(i)}
                y={y(p.value) - 14}
                textAnchor="middle"
                style={{ fill: "var(--text-1)", font: "700 13px var(--font-sans)" }}
              >
                {p.label}
              </text>
            )}
            <text
              x={x(i)}
              y={H - 8}
              textAnchor="middle"
              style={{ fill: "var(--text-3)", font: "500 12px var(--font-mono)" }}
            >
              {p.chapterIdx}장
            </text>
          </g>
        ))}
      </svg>
    </Card>
  );
}
