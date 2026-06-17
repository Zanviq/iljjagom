import { EmptyState } from "@/components/ui/EmptyState";

/**
 * 계약 확정 대기 중인 콘솔 탭 자리표시. 무엇을 보여줄 화면인지(왜 비어있는지)를 안내한다.
 * 백엔드가 해당 admin API를 03-기능명세서 §4/§7에 확정하면 이 자리표시를 실데이터 뷰로 교체.
 */
export function Pending({
  title,
  describe,
  endpoint,
}: {
  title: string;
  describe: string;
  endpoint: string;
}) {
  return (
    <div>
      <h1 className="text-3xl font-extrabold">{title}</h1>
      <p className="mt-1 text-muted">{describe}</p>
      <EmptyState className="mt-6 text-left">
        <p className="font-bold text-foreground">백엔드 계약 확정 대기 중</p>
        <p className="mt-2">
          이 화면은 <code className="rounded bg-black/5 px-1">{endpoint}</code>{" "}
          응답을 표시합니다. 해당 API가 <code>03-기능명세서</code> §4/§7에 확정되면
          실데이터로 연결됩니다. (handoff/requests.md OPEN)
        </p>
      </EmptyState>
    </div>
  );
}
