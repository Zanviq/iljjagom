import { Pending } from "@/components/admin/Pending";

export default function ConsoleUsagePage() {
  return (
    <Pending
      title="토큰·비용"
      describe="모델별·역할별·일자별 토큰과 예상 비용 추세. 세션 단위로 드릴다운해요."
      endpoint="GET /admin/usage/tokens"
    />
  );
}
