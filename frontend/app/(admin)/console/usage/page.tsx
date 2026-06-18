import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
import { getTokenUsage } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";
import type { TokenUsageReport } from "@/lib/types";

function cost(n: number): string {
  return `$${n.toFixed(4)}`;
}

export default async function ConsoleUsagePage() {
  const token = await getAccessToken();
  let report: TokenUsageReport | null = null;
  let error: string | null = null;
  try {
    report = await getTokenUsage(token, "model");
  } catch (e) {
    error = e instanceof Error ? e.message : "사용량을 불러오지 못했어요.";
  }

  return (
    <div>
      <p className="ijg-eyebrow mb-4 text-ink-3">토큰·비용 · 모델별 토큰과 예상 비용</p>
      {error ? (
        <ErrorText className="mt-2">{error}</ErrorText>
      ) : !report || report.buckets.length === 0 ? (
        <EmptyState icon="coins" title="집계된 사용량이 없어요" />
      ) : (
        <div className="overflow-x-auto rounded-[var(--radius-card)] border border-line">
          <table
            className="w-full min-w-[40rem] border-collapse bg-surface text-left"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            <thead>
              <tr className="border-b border-line bg-surface-2">
                {["모델", "호출", "입력 토큰", "출력 토큰", "예상 비용"].map((h) => (
                  <th key={h} className="ijg-eyebrow p-3 text-ink-3" style={{ textAlign: "left" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="text-[length:var(--text-sm)] text-ink">
              {report.buckets.map((b) => (
                <tr key={b.key} className="border-b border-line-soft">
                  <td className="p-3 font-bold">{b.key}</td>
                  <td className="p-3">{b.calls}</td>
                  <td className="p-3">{b.tokensIn}</td>
                  <td className="p-3">{b.tokensOut}</td>
                  <td className="p-3">{cost(b.estCost)}</td>
                </tr>
              ))}
              <tr className="bg-surface-2 font-bold">
                <td className="p-3">합계</td>
                <td className="p-3">{report.total.calls}</td>
                <td className="p-3">{report.total.tokensIn}</td>
                <td className="p-3">{report.total.tokensOut}</td>
                <td className="p-3">{cost(report.total.estCost)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
