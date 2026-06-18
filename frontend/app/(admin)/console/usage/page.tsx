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
      <h1 className="text-3xl font-extrabold">토큰·비용</h1>
      <p className="mt-1 text-muted">모델별 토큰과 예상 비용이에요.</p>
      {error ? (
        <ErrorText className="mt-6">{error}</ErrorText>
      ) : !report || report.buckets.length === 0 ? (
        <EmptyState className="mt-6">집계된 사용량이 없어요.</EmptyState>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-card ring-1 ring-border">
          <table className="w-full min-w-[40rem] border-collapse bg-surface text-left">
            <thead>
              <tr className="border-b border-border text-sm text-muted">
                <th className="p-3 font-bold">모델</th>
                <th className="p-3 font-bold">호출</th>
                <th className="p-3 font-bold">입력 토큰</th>
                <th className="p-3 font-bold">출력 토큰</th>
                <th className="p-3 font-bold">예상 비용</th>
              </tr>
            </thead>
            <tbody>
              {report.buckets.map((b) => (
                <tr key={b.key} className="border-b border-border">
                  <td className="p-3 text-sm font-bold">{b.key}</td>
                  <td className="p-3 text-sm">{b.calls}</td>
                  <td className="p-3 text-sm">{b.tokensIn}</td>
                  <td className="p-3 text-sm">{b.tokensOut}</td>
                  <td className="p-3 text-sm">{cost(b.estCost)}</td>
                </tr>
              ))}
              <tr className="bg-background font-bold">
                <td className="p-3 text-sm">합계</td>
                <td className="p-3 text-sm">{report.total.calls}</td>
                <td className="p-3 text-sm">{report.total.tokensIn}</td>
                <td className="p-3 text-sm">{report.total.tokensOut}</td>
                <td className="p-3 text-sm">{cost(report.total.estCost)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
